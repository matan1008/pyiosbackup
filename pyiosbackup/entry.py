from dataclasses import dataclass
from datetime import datetime
import pathlib
import posixpath

from packaging.version import Version
from cryptography.hazmat.primitives import padding

FILE_DATA_PAD_BITS = 128  # Files data is 128 bits (16 bytes) padded.
MODE_TYPE_MASK = 0xE000
MODE_TYPE_SYMLINK = 0xA000
MODE_TYPE_FILE = 0x8000
MODE_TYPE_DIR = 0x4000


@dataclass
class Entry:
    backup: 'pyiosbackup.backup.Backup'  # noqa: F821
    file_id: str
    domain: str
    relative_path: str
    last_modified: datetime
    created: datetime
    last_status_change: datetime
    size: int
    mode: int
    group_id: int
    user_id: int
    encryption_key: bytes

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
        return self.backup.path

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
        if self.backup.ios_version > Version('10.2'):
            return pathlib.Path(self.file_id[:2]) / self.file_id
        else:
            return pathlib.Path(self.file_id)

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
        if not self.backup.is_encrypted:
            return encrypted
        decrypted = self.backup.keybag.decrypt(encrypted, self.encryption_key)
        unpadder = padding.PKCS7(FILE_DATA_PAD_BITS).unpadder()
        decrypted = unpadder.update(decrypted) + unpadder.finalize()
        return decrypted

    def is_dir(self) -> bool:
        """
        Check if entry is a directory.
        """
        return self.mode & MODE_TYPE_MASK == MODE_TYPE_DIR

    def is_file(self) -> bool:
        """
        Check if entry is a file.
        """
        return self.mode & MODE_TYPE_MASK == MODE_TYPE_FILE

    def iterdir(self, enforce_domain: bool = True):
        """
        When the entry points to a directory, yield path objects of the directory contents.
        :param enforce_domain: Yield only contents from the same domain.
        """
        if not self.is_dir():
            raise ValueError('Can\'t listdir a file')
        for entry in self.backup.iter_entries():
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
