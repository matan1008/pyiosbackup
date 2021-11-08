from dataclasses import dataclass
from datetime import datetime, timezone
import pathlib
import posixpath

from bpylist2 import archiver
from cryptography.hazmat.primitives import padding

FILE_DATA_PAD_BITS = 128  # Files data is 128 bits (16 bytes) padded.
FLAG_FILE = 1
FLAG_DIRECTORY = 2


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


class Entry:
    def __init__(self, metadata, backup):
        """
        Create a backup entry.
        :param metadata: Entry's metadata (from Files table in Manifest.db).
        :param pyiosbackup.backup.Backup backup: Backup object.
        """
        self._backup = backup
        self.file_id = metadata['fileID']
        self.domain = metadata['domain']
        self.flags = metadata['flags']
        mb_info = archiver.unarchive(metadata['file'])  # type: MBFile
        self.relative_path = mb_info.relative_path
        assert metadata['relativePath'] == self.relative_path
        self.last_modified = datetime.fromtimestamp(mb_info.last_modified, timezone.utc)
        self.created = datetime.fromtimestamp(mb_info.created, timezone.utc)
        self.last_status_change = datetime.fromtimestamp(mb_info.last_status_change, timezone.utc)
        self.size = mb_info.size
        self.mode = mb_info.mode
        self.group_id = mb_info.group_id
        self.user_id = mb_info.user_id
        self.encryption_key = mb_info.encryption_key

    @property
    def name(self) -> str:
        """
        A string representing the final path component, excluding the drive and root, if any.
        For example: 'trustd/private/TrustStore.sqlite3' -> 'TrustStore.sqlite3'
        """
        return self.filename.name

    @property
    def suffix(self) -> str:
        """
        The file extension of the final component, if any.
        For example: 'trustd/private/TrustStore.sqlite3' -> '.sqlite3'
        """
        return self.filename.suffix

    @property
    def suffixes(self):
        """
        A list of the path’s file extensions.
        For example: 'trustd/private/TrustStore.sqlite3' -> ['.sqlite3']
        :rtype: list
        """
        return self.filename.suffixes

    @property
    def stem(self) -> str:
        """
        The final path component, without its suffix.
        For example: 'trustd/private/TrustStore.sqlite3' -> 'TrustStore'
        """
        return self.filename.stem

    @property
    def filename(self) -> pathlib.Path:
        """
        Relative file path of the entry.
        """
        return pathlib.Path(self.relative_path)

    @property
    def root(self) -> pathlib.Path:
        """
        Path to the backup directory.
        """
        return self._backup.path

    @property
    def real_path(self) -> pathlib.Path:
        """
        Real path of entry file.
        """
        return self.root / self.hash_path

    @property
    def hash_path(self) -> pathlib.Path:
        """
        Relative path of the entry file (from the backup directory).
        """
        return pathlib.Path(self.file_id[:2]) / self.file_id

    def read_text(self, encoding: str = 'utf-8', errors: str = 'strict') -> str:
        """
        Read decrypted entry data as text.
        :param encoding: The encoding with which to decode the bytes.
        :param errors: The error handling scheme to use for the handling of decoding errors.
        :return: Decrypted and decoded entry data.
        """
        return self.read_bytes().decode(encoding, errors)

    def read_raw(self) -> bytes:
        """
        Read raw entry data.
        """
        return self.real_path.read_bytes()

    def read_bytes(self) -> bytes:
        """
        Read decrypted entry data.
        """
        encrypted = self.read_raw()
        if not self._backup.is_encrypted():
            return encrypted
        decrypted = self._backup.keybag.decrypt(encrypted, self.encryption_key)
        unpadder = padding.PKCS7(FILE_DATA_PAD_BITS).unpadder()
        decrypted = unpadder.update(decrypted) + unpadder.finalize()
        return decrypted

    def is_dir(self) -> bool:
        """
        Check if entry is a directory.
        """
        return self.flags == FLAG_DIRECTORY

    def is_file(self) -> bool:
        """
        Check if entry is a file.
        """
        return self.flags == FLAG_FILE

    def iterdir(self, enforce_domain: bool = True):
        """
        When the entry points to a directory, yield path objects of the directory contents.
        :param enforce_domain: Yield only contents from the same domain.
        """
        if not self.is_dir():
            raise ValueError('Can\'t listdir a file')
        for entry in self._backup.iter_entries():
            if enforce_domain and entry.domain != self.domain:
                continue
            if entry.relative_path == self.relative_path:
                continue
            if posixpath.dirname(entry.relative_path.rstrip('/')) != self.relative_path.rstrip('/'):
                continue
            yield entry

    def __str__(self):
        return str(self.filename)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.root}, {self.relative_path}, {self.domain})'
