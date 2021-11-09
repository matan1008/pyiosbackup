import hashlib
import logging

from construct import Bytes, this, Int32ub, GreedyRange, IfThenElse
from packaging.version import Version
from construct import Struct, GreedyBytes, Int32ul
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

logger = logging.getLogger('pyiosbackup')

encryption_key_struct = Struct(
    'class_' / Int32ul,
    'key' / GreedyBytes
)

keybag_struct = GreedyRange(Struct(
    'tag' / Bytes(4),
    'size' / Int32ub,
    'data' / IfThenElse(this.size == Int32ub.sizeof(), Int32ub, Bytes(this.size)),
))


def aes_decrypt_wrapped(wrapping_key: bytes, key: bytes, encrypted: bytes) -> bytes:
    """
    Decrypt data with wrapped key.
    :param wrapping_key: Wrapping key to unwrap the key with.
    :param key: Wrapped key to decrypt data with.
    :param encrypted: Encrypted data.
    :return: Decrypted data.
    """
    key = aes_key_unwrap(wrapping_key, key)
    cipher = Cipher(algorithms.AES(key), modes.CBC(b'\x00' * 16))
    decryptor = cipher.decryptor()
    return decryptor.update(encrypted) + decryptor.finalize()


class Keybag:
    CLASS_ELEMENTS_COUNT = 5

    def __init__(self, wrapping_keys):
        """
        Create a keybag instance.
        :param dict wrapping_keys: Mapping between classes and their wrapping keys.
        """
        self._wrapping_keys = wrapping_keys

    @staticmethod
    def from_manifest(manifest, password: str):
        """
        Create a keybag object from a Manifest.plist.
        :param dict manifest: Loaded Manifest.plist file.
        :param password: Password to encrypted backup.
        :return: Keybag object.
        :rtype: Keybag
        """
        keybag = keybag_struct.parse(manifest['BackupKeyBag'])
        # The class count excludes the root class (first class in the keybag) and is one based.
        class_count = [e.data for e in keybag if e.tag == b'CLAS'][0] - 1
        logger.debug(f'Found {class_count} key classes')
        classes_index = len(keybag) - (Keybag.CLASS_ELEMENTS_COUNT * class_count)
        decryption_key = Keybag._decryption_key_from_password(password, keybag[:classes_index], manifest)
        logger.debug(f'Using decryption key {decryption_key.hex()}')

        classes_keys = {}
        for cls_offset in range(classes_index, len(keybag), Keybag.CLASS_ELEMENTS_COUNT):
            current_class_data = keybag[cls_offset:cls_offset + Keybag.CLASS_ELEMENTS_COUNT]
            classes_keys.update(Keybag._parse_class_key(current_class_data, decryption_key))

        return Keybag(classes_keys)

    def decrypt(self, data: bytes, key: bytes) -> bytes:
        """
        Decrypt data.
        :param data: Encrypted data.
        :param key: Wrapped key struct.
        :return: Decrypted data.
        """
        parsed_key = encryption_key_struct.parse(key)
        return aes_decrypt_wrapped(self.get_key(parsed_key.class_), parsed_key.key, data)

    def get_key(self, class_) -> bytes:
        """
        Get a decryption for a class.
        :param class_:
        :return:
        """
        return self._wrapping_keys[class_]

    @staticmethod
    def _decryption_key_from_password(password: str, root_elements, manifest) -> bytes:
        """
        Create a decryption key.
        :param password: Password to encrypted backup.
        :param root_elements: Root elements of keybag.
        :param dict manifest: Loaded Manifest.plist file.
        :return: Decryption key.
        """
        password = password.encode('utf-8')
        root_keys = {key.tag: key.data for key in root_elements}
        logger.debug(f'Using root elements {root_keys}')
        if Version(manifest['Lockdown']['ProductVersion']) > Version('10.2'):
            password = hashlib.pbkdf2_hmac('sha256', password, root_keys[b'DPSL'], root_keys[b'DPIC'], 32)
        return hashlib.pbkdf2_hmac('sha1', password, root_keys[b'SALT'], root_keys[b'ITER'], 32)

    @staticmethod
    def _parse_class_key(class_data, decryption_key: bytes):
        """
        Parse class key.
        :param class_data: Elements of a specific class.
        :param decryption_key: Decryption key for class keys.
        :return: Mapping between class to its decryption key.
        :rtype: dict
        """
        current_class_data = {key.tag: key.data for key in class_data}
        if current_class_data[b'WRAP'] & 2 and b'WPKY' in current_class_data:
            return {current_class_data[b'CLAS']: aes_key_unwrap(decryption_key, current_class_data[b'WPKY'])}
        return {}
