from pathlib import Path

from packaging.version import Version

from pyiosbackup.manifest_dbs.manifest_db_interface import ManifestDb
from pyiosbackup.manifest_dbs.sqlite3 import ManifestDbSqlite3
from pyiosbackup.manifest_dbs.mbdb import ManifestDbMbdb


def from_path(backup_path: Path, manifest, keybag) -> ManifestDb:
    """
    Load the Manifest.db.
    :param backup_path: Path to backup folder.
    :param manifest: Loaded Manifest.plist file.
    :param keybag: Backup keybag.
    :return: Manifest.db object.
    """
    if manifest.product_version > Version('10.2'):
        return ManifestDbSqlite3.from_path(backup_path / ManifestDbSqlite3.NAME, manifest, keybag)
    else:
        return ManifestDbMbdb.from_path(backup_path / ManifestDbMbdb.NAME, manifest, keybag)
