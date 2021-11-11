from pyiosbackup.keybag import Keybag
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
