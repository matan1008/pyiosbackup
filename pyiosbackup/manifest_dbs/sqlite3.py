from pathlib import Path
from datetime import datetime, timezone
import sqlite3
import tempfile
import logging
from dataclasses import dataclass

from bpylist2 import archiver

from pyiosbackup.exceptions import MissingEntryError
from pyiosbackup.manifest_dbs.manifest_db_interface import ManifestDb

ENTRIES_QUERY = 'SELECT * FROM Files'

logger = logging.getLogger('pyiosbackup')


@dataclass
class MBFile:
    relative_path: str
    last_modified: int
    last_status_change: int
    created: int
    size: int
    mode: int
    group_id: int
    user_id: int
    encryption_key: bytes = b''

    @staticmethod
    def decode_archive(archive_obj):
        return MBFile(
            relative_path=archive_obj.decode('RelativePath'),
            last_modified=archive_obj.object['LastModified'],
            last_status_change=archive_obj.object['LastStatusChange'],
            created=archive_obj.object['Birth'],
            size=archive_obj.object['Size'],
            mode=archive_obj.object['Mode'],
            group_id=archive_obj.object['GroupID'],
            user_id=archive_obj.object['UserID'],
            encryption_key=archive_obj.decode('EncryptionKey').NSdata if 'EncryptionKey' in archive_obj.object else b'',
        )


archiver.update_class_map({'MBFile': MBFile})


class ManifestDbSqlite3(ManifestDb):
    NAME = 'Manifest.db'

    def __init__(self, path: Path):
        super().__init__(path)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row

    @classmethod
    def from_path(cls, path: Path, manifest, keybag):
        manifest_db = path.read_bytes()
        if manifest.is_encrypted:
            manifest_db = keybag.decrypt(manifest_db, manifest.manifest_key)
        manifest_db_file = tempfile.NamedTemporaryFile(suffix='sqlite3', delete=False)
        logger.debug(f'Writing decrypted backup to {manifest_db_file.name}')
        manifest_db_file.write(manifest_db)
        return cls(Path(manifest_db_file.name))

    def get_metadata_by_id(self, file_id: str):
        return self._fetch_one_entry(f'{ENTRIES_QUERY} WHERE fileID=\'{file_id}\'')

    def get_metadata_by_domain_and_path(self, domain: str, relative_path: str):
        return self._fetch_one_entry(f'{ENTRIES_QUERY} WHERE domain=\'{domain}\' AND relativePath=\'{relative_path}\'')

    def get_all_entries(self):
        return map(self._load_entry, self._cursor.execute(f'{ENTRIES_QUERY} ORDER BY relativePath').fetchall())

    @property
    def _cursor(self):
        return self._conn.cursor()

    def _fetch_one_entry(self, query):
        result = self._cursor.execute(query).fetchone()
        if result is None:
            raise MissingEntryError()
        return self._load_entry(result)

    @staticmethod
    def _load_entry(entry):
        mb_info = archiver.unarchive(entry['file'])  # type: MBFile
        return {
            'file_id': entry['fileID'],
            'domain': entry['domain'],
            'relative_path': entry['relativePath'],
            'last_modified': datetime.fromtimestamp(mb_info.last_modified, timezone.utc),
            'created': datetime.fromtimestamp(mb_info.created, timezone.utc),
            'last_status_change': datetime.fromtimestamp(mb_info.last_status_change, timezone.utc),
            'size': mb_info.size,
            'mode': mb_info.mode,
            'group_id': mb_info.group_id,
            'user_id': mb_info.user_id,
            'encryption_key': mb_info.encryption_key,
        }
