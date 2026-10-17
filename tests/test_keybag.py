import pytest
from bytestruct import TruncatedDataError

from pyiosbackup.keybag import EncryptionKey, Keybag, KeybagItem, parse_keybag
from pyiosbackup.manifest_plist import ManifestPlist


def test_creating_from_manifest(manifest_keybag_zeros):
    keybag = Keybag.from_manifest(
        ManifestPlist({'BackupKeyBag': manifest_keybag_zeros, 'Lockdown': {'ProductVersion': '10.3'}}),
        '0000'
    )
    for i in range(1, 11):
        assert keybag.get_key(i) == 32 * b'\x00'


def test_decrypting_data(manifest_keybag_zeros):
    keybag = Keybag.from_manifest(
        ManifestPlist({'BackupKeyBag': manifest_keybag_zeros, 'Lockdown': {'ProductVersion': '10.3'}}),
        '0000'
    )
    key = (b'\x02\x00\x00\x00\x971t\x9448\x07\xe6\x90\xfd\x1eC\x14\x13\x96=\xc0\xe3\xde\xb4\x90\x7f\xb8\x9f\xa3l'
           b'\xe6Q&\xd0\xea\x13\x018\x1f\xb3\xa2\x94\x1e/')
    encrypted_data = b'x\xb5\x1c\xa57L:\xd5u\x17B\x88h\x8c\xdaI'
    assert keybag.decrypt(encrypted_data, key) == b'Test data\x07\x07\x07\x07\x07\x07\x07'


def test_parsing_keybag(manifest_keybag_zeros):
    items = parse_keybag(manifest_keybag_zeros)
    assert len(items) == 65
    assert items[0] == KeybagItem(b'VERS', 5)
    assert items[2] == KeybagItem(b'UUID', 16 * b'\x00')
    assert items[11] == KeybagItem(b'CLAS', 11)


def test_parsing_keybag_stops_at_truncated_item():
    data = b'ITER\x00\x00\x00\x04\x00\x00\x27\x10' + b'SALT\x00\x00\x00\x14' + 4 * b'\x00'
    assert parse_keybag(data) == [KeybagItem(b'ITER', 10000)]
    assert parse_keybag(b'') == []


def test_building_keybag_item():
    for item in (KeybagItem(b'ITER', 10000), KeybagItem(b'SALT', 20 * b'\x01'), KeybagItem(b'EMPT', b'')):
        assert parse_keybag(item.build()) == [item]


def test_parsing_encryption_key():
    key = EncryptionKey.parse(b'\x02\x00\x00\x00' + 40 * b'\xaa')
    assert key == EncryptionKey(2, 40 * b'\xaa')
    with pytest.raises(TruncatedDataError):
        EncryptionKey.parse(b'\x02\x00')
