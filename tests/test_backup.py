from datetime import datetime, timezone
from pathlib import Path
import plistlib

from pyiosbackup import Backup
from pyiosbackup.backup import MANIFEST_DB_PATH, MANIFEST_PLIST_PATH, STATUS_PLIST_PATH, INFO_PLIST_PATH


def test_creating_from_path(tmp_path, manifest_keybag_zeros):
    (tmp_path / MANIFEST_DB_PATH).write_bytes((Path(__file__).parent / 'encrypted_test_db.bin').read_bytes())
    manifest_plist = tmp_path / MANIFEST_PLIST_PATH
    manifest_plist.write_bytes(plistlib.dumps({
        'BackupKeyBag': manifest_keybag_zeros,
        'Lockdown': {'ProductVersion': '10.3'},
        'ManifestKey': (b'\x02\x00\x00\x00\x971t\x9448\x07\xe6\x90\xfd\x1eC\x14\x13\x96=\xc0\xe3\xde\xb4\x90\x7f\xb8'
                        b'\x9f\xa3l\xe6Q&\xd0\xea\x13\x018\x1f\xb3\xa2\x94\x1e/')
    }))
    (tmp_path / INFO_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / STATUS_PLIST_PATH).write_bytes(plistlib.dumps({}))
    (tmp_path / '57').mkdir()
    (tmp_path / '57' / '5727bd1c5fa1055e15d8b4a75a74793c84b5ffdc').write_bytes(
        b'x\xb5\x1c\xa57L:\xd5u\x17B\x88h\x8c\xdaI')
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
    assert file.mode == 6877
    assert file.group_id == 501
    assert file.user_id == 501
    assert file.read_text() == 'Test data'
