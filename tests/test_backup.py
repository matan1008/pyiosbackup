from datetime import datetime, timezone
from pathlib import Path
import plistlib

import pytest

from pyiosbackup import Backup
from pyiosbackup.exceptions import BackupPasswordIsRequired, MissingEntryError
from pyiosbackup.backup import STATUS_PLIST_PATH, INFO_PLIST_PATH
from pyiosbackup.manifest_plist import ManifestPlist
from pyiosbackup.manifest_dbs.sqlite3 import ManifestDbSqlite3
from pyiosbackup.manifest_dbs.mbdb import ManifestDbMbdb


@pytest.fixture(scope='function')
def backup(tmp_path, manifest_keybag_zeros):
    (tmp_path / ManifestDbSqlite3.NAME).write_bytes((Path(__file__).parent / 'encrypted_sqlite3_db.bin').read_bytes())
    manifest_plist = tmp_path / ManifestPlist.NAME
    manifest_plist.write_bytes(plistlib.dumps({
        'BackupKeyBag': manifest_keybag_zeros,
        'IsEncrypted': True,
        'Lockdown': {'ProductVersion': '10.3'},
        'ManifestKey': (b'\x02\x00\x00\x00\x971t\x9448\x07\xe6\x90\xfd\x1eC\x14\x13\x96=\xc0\xe3\xde\xb4\x90\x7f\xb8'
                        b'\x9f\xa3l\xe6Q&\xd0\xea\x13\x018\x1f\xb3\xa2\x94\x1e/')
    }))
    (tmp_path / INFO_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / STATUS_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / '57').mkdir()
    (tmp_path / '57' / '5727bd1c5fa1055e15d8b4a75a74793c84b5ffdc').write_bytes(
        b'x\xb5\x1c\xa57L:\xd5u\x17B\x88h\x8c\xdaI')
    return tmp_path


def test_creating_from_path_sqlite3(backup):
    b = Backup.from_path(backup, '0000')
    files = list(b.iter_files())
    assert len(files) == 1
    file = files[0]
    assert file.relative_path == 'Media/Test.txt'
    assert file.file_id == '5727bd1c5fa1055e15d8b4a75a74793c84b5ffdc'
    assert file.domain == 'MyTestDomain'
    assert file.is_file()
    assert file.filename == Path('Media/Test.txt')
    assert file.last_modified == datetime.fromtimestamp(1628082463, timezone.utc)
    assert file.last_status_change == datetime.fromtimestamp(1628082509, timezone.utc)
    assert file.created == datetime.fromtimestamp(1627974948, timezone.utc)
    assert file.size == 9
    assert file.mode == 33261
    assert file.group_id == 501
    assert file.user_id == 501
    assert file.read_text() == 'Test data'


def test_missing_entry(backup):
    b = Backup.from_path(backup, '0000')
    with pytest.raises(MissingEntryError):
        b.get_entry_by_domain_and_path('unknown-domain', 'unknown-path')


example_mbdb = (
    b'mbdb'
    b'\x05\x00'
    # Domain
    b'\x00\x0c'
    b'MyTestDomain'
    # Filename
    b'\x00\x0e'
    b'Media/Test.txt'
    # Filename
    b'\xff\xff'
    # Hash
    b'\xff\xff'
    # Encryption key
    b'\x00\x2c'
    b'\x04\x00\x00\x00\x971t\x9448\x07\xe6\x90\xfd\x1eC\x14\x13\x96=\xc0\xe3\xde\xb4\x90\x7f\xb8\x9f\xa3l\xe6Q&\xd0'
    b'\xea\x13\x018\x1f\xb3\xa2\x94\x1e/'
    # Mode
    b'\x81\xed'
    b'\x00\x00\x00\x00'
    b'\x00\x00\x12\xD8'
    # User id
    b'\x00\x00\x01\xF5'
    # Group id
    b'\x00\x00\x01\xF5'
    # mtime
    b'\x61\x0a\x91\x1f'
    # atime
    b'\x61\x0a\x91\x4d'
    # ctime
    b'\x61\x08\xed\x24'
    # size
    b'\x00\x00\x00\x00\x00\x00\x00\x09'
    b'\x04'
    b'\x00'

)


def test_creating_from_path_mbdb(tmp_path, manifest_keybag_zeros_before_10_2):
    (tmp_path / ManifestDbMbdb.NAME).write_bytes(example_mbdb)
    manifest_plist = tmp_path / ManifestPlist.NAME
    manifest_plist.write_bytes(plistlib.dumps({
        'BackupKeyBag': manifest_keybag_zeros_before_10_2,
        'IsEncrypted': True,
        'Lockdown': {'ProductVersion': '9.0.1'},
    }))
    (tmp_path / INFO_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / STATUS_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / '5727bd1c5fa1055e15d8b4a75a74793c84b5ffdc').write_bytes(b'x\xb5\x1c\xa57L:\xd5u\x17B\x88h\x8c\xdaI')
    b = Backup.from_path(tmp_path, '0000')
    files = list(b.iter_files())
    assert len(files) == 1
    file = files[0]
    assert file.relative_path == 'Media/Test.txt'
    assert file.file_id == '5727bd1c5fa1055e15d8b4a75a74793c84b5ffdc'
    assert file.domain == 'MyTestDomain'
    assert file.is_file()
    assert file.filename == Path('Media/Test.txt')
    assert file.last_modified == datetime.fromtimestamp(1628082463, timezone.utc)
    assert file.last_status_change == datetime.fromtimestamp(1628082509, timezone.utc)
    assert file.created == datetime.fromtimestamp(1627974948, timezone.utc)
    assert file.size == 9
    assert file.mode == 33261
    assert file.group_id == 501
    assert file.user_id == 501
    assert file.read_text() == 'Test data'


def test_missing_entry_mbdb(tmp_path, manifest_keybag_zeros_before_10_2):
    (tmp_path / ManifestDbMbdb.NAME).write_bytes(example_mbdb)
    manifest_plist = tmp_path / ManifestPlist.NAME
    manifest_plist.write_bytes(plistlib.dumps({
        'BackupKeyBag': manifest_keybag_zeros_before_10_2,
        'IsEncrypted': True,
        'Lockdown': {'ProductVersion': '9.0.1'},
    }))
    (tmp_path / INFO_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / STATUS_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / '5727bd1c5fa1055e15d8b4a75a74793c84b5ffdc').write_bytes(b'x\xb5\x1c\xa57L:\xd5u\x17B\x88h\x8c\xdaI')
    b = Backup.from_path(tmp_path, '0000')
    with pytest.raises(MissingEntryError):
        b.get_entry_by_domain_and_path('unknown-domain', 'unknown-path')


def test_not_supplying_password(backup):
    with pytest.raises(BackupPasswordIsRequired):
        Backup.from_path(backup)
