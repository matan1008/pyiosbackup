from pathlib import Path
import logging
import plistlib
import shutil
import sqlite3
import tempfile

from packaging.version import Version

from pyiosbackup.entry import Entry
from pyiosbackup.keybag import Keybag

MANIFEST_PLIST_PATH = 'Manifest.plist'
INFO_PLIST_PATH = 'Info.plist'
STATUS_PLIST_PATH = 'Status.plist'
MANIFEST_DB_PATH = 'Manifest.db'

ENTRIES_QUERY = 'SELECT * FROM Files'

logger = logging.getLogger('pyiosbackup')
logger.addHandler(logging.NullHandler())


class Backup:
    def __init__(self, backup_path: Path, manifest_db_path: Path, status, info, keybag: Keybag = None):
        """
        Create a Backup object.
        :param backup_path: Path to the original backup.
        :param manifest_db_path: Path to a decrypted Manifest.db.
        :param dict status: Loaded Status.plist.
        :param dict info: Loaded Info.plist.
        :param dict keybag: Decryption keybag, None if backup is not encrypted.
        """
        self.path = backup_path
        self.keybag = keybag
        self._manifest_db_path = manifest_db_path
        self._manifest_db_conn = sqlite3.connect(str(manifest_db_path))
        self._manifest_db_conn.row_factory = sqlite3.Row
        self._status = status
        self._info = info

    @staticmethod
    def from_path(backup_path: Path, password: str = ''):
        """
        Create a backup object from a backup directory.
        :param backup_path: Path to a backup directory.
        :param password: Password to decrypt backup, if not encrypted password should be an empty string.
        :return: Backup object.
        :rtype: Backup
        """
        logger.info(f'Creating backup from {backup_path}')

        backup_path = Path(backup_path)
        manifest_db = (backup_path / MANIFEST_DB_PATH).read_bytes()

        if not password:
            logger.info(f'Password is empty, continue as decrypted backup')
            return Backup.from_manifest_db(backup_path, manifest_db)

        manifest = plistlib.loads((backup_path / MANIFEST_PLIST_PATH).read_bytes())
        keybag = Keybag.from_manifest(manifest, password)
        if Version(manifest['Lockdown']['ProductVersion']) > Version('10.2'):
            manifest_db = keybag.decrypt(manifest_db, manifest['ManifestKey'])
        return Backup.from_manifest_db(backup_path, manifest_db, keybag)

    @staticmethod
    def from_manifest_db(backup_path: Path, manifest_db: bytes, keybag: Keybag = None):
        """
        Create a backup object from a backup directory and decrypted Manifest.db.
        :param backup_path: Path to a backup directory.
        :param manifest_db: Decrypted data of Manifest.db file.
        :param keybag: Decryption keybag for when backup is decrypted.
        :return: Backup object.
        :rtype: Backup
        """
        info = plistlib.loads((backup_path / INFO_PLIST_PATH).read_bytes())
        status = plistlib.loads((backup_path / STATUS_PLIST_PATH).read_bytes())
        manifest_db_file = tempfile.NamedTemporaryFile(suffix='sqlite3', delete=False)
        logger.debug(f'Writing decrypted backup to {manifest_db_file.name}')
        manifest_db_file.write(manifest_db)
        return Backup(backup_path, Path(manifest_db_file.name), status, info, keybag)

    @property
    def date(self):
        """
        :rtype: datetime.datetime
        """
        return self._status['Date']

    @property
    def version(self) -> str:
        return self._status['Version']

    @property
    def target_identifier(self) -> str:
        return self._info['Target Identifier']

    @property
    def ios_version(self) -> str:
        return self._info['Product Version']

    @property
    def installed_apps(self):
        return self._info['Installed Applications']

    @property
    def imei(self) -> str:
        return self._info['IMEI']

    @property
    def itunes_version(self) -> str:
        return self._info['iTunes Version']

    def extract_all(self, path='.'):
        """
        Extract all decrypted files from a backup.
        :param path: Path to destination directory.
        """
        logger.info(f'Extracting backup to {path}')
        dest_dir = Path(path)
        dest_dir.mkdir(exist_ok=True, parents=True)
        # Copy all metadata files.
        shutil.copy2(self.path / MANIFEST_PLIST_PATH, dest_dir / MANIFEST_PLIST_PATH)
        shutil.copy2(self.path / INFO_PLIST_PATH, dest_dir / INFO_PLIST_PATH)
        shutil.copy2(self.path / STATUS_PLIST_PATH, dest_dir / STATUS_PLIST_PATH)
        shutil.copy2(self._manifest_db_path, dest_dir / MANIFEST_DB_PATH)

        for file in self.iter_files():
            dest_file = dest_dir / file.hash_path
            logger.debug(f'Extracting file {file.filename} to {dest_file}')
            dest_file.parent.mkdir(exist_ok=True, parents=True)
            dest_file.write_bytes(file.read_bytes())

    def extract_file_id(self, file_id: str, path='.'):
        """
        Extract a file by its id.
        :param file_id: File ID.
        :param path: Path to destination directory.
        """
        entry = self.get_entry_by_id(file_id)
        dest = Path(path)
        if dest.is_dir():
            dest /= entry.name
        dest.parent.mkdir(exist_ok=True, parents=True)
        dest.write_bytes(entry.read_bytes())

    def extract_domain_and_path(self, domain: str, relative_path: str, path='.'):
        """
        Extract a file by its domain and path.
        :param domain: File's domain, e.g. 'RootDomain'.
        :param relative_path: File's relative path, e.g. 'Library/Preferences/com.apple.backupd.plist'.
        :param path: Path to destination directory.
        """
        entry = self.get_entry_by_domain_and_path(domain, relative_path)
        dest = Path(path)
        if dest.is_dir():
            dest /= entry.name
        dest.parent.mkdir(exist_ok=True, parents=True)
        dest.write_bytes(entry.read_bytes())

    def get_entry_by_id(self, file_id: str) -> Entry:
        """
        Get an entry by its id.
        :param file_id: Entry's ID.
        :return: Parsed entry object.
        """
        metadata = self._manifest_db_conn.cursor().execute(f'{ENTRIES_QUERY} WHERE fileID=\'{file_id}\'').fetchone()
        return Entry(metadata, self)

    def get_entry_by_domain_and_path(self, domain: str, relative_path: str) -> Entry:
        """
        Get an entry by its domain and path.
        :param domain: File's domain, e.g. 'RootDomain'.
        :param relative_path: File's relative path, e.g. 'Library/Preferences/com.apple.backupd.plist'.
        :return: Parsed entry object.
        """
        metadata = self._manifest_db_conn.cursor().execute(
            f'{ENTRIES_QUERY} WHERE domain=\'{domain}\' AND relativePath=\'{relative_path}\''
        ).fetchone()
        return Entry(metadata, self)

    def iter_entries(self):
        """
        Iter over all entries in backup.
        """
        entries = self._manifest_db_conn.cursor().execute(f'{ENTRIES_QUERY} ORDER BY relativePath').fetchall()
        for metadata in entries:
            yield Entry(metadata, self)

    def iter_files(self):
        """
        Iter over all files in backup.
        """
        return filter(lambda f: f.is_file(), self.iter_entries())

    def is_encrypted(self) -> bool:
        """
        Test if backup is encrypted.
        :return: True if encrypted, False otherwise.
        """
        return self.keybag is not None

    def stats(self):
        """
        Collect statistics about the current backup.
        :return: Creation date, backup version, target identifier, iOS version, IMEI, iTunes version, backup path,
        entries count, files count and backup size.
        :rtype: dict
        """
        size = 0
        count = 0
        files_count = 0
        for entry in self.iter_entries():
            count += 1
            size += entry.size
            if entry.is_file():
                files_count += 1

        return {
            'date': self.date,
            'version': self.version,
            'target_identifier': self.target_identifier,
            'ios_version': self.ios_version,
            'installed_apps': self.installed_apps,
            'imei': self.imei,
            'itunes_version': self.itunes_version,
            'path': self.path,
            'count': count,
            'files_count': files_count,
            'size': size,
        }
