from pathlib import Path
import plistlib

from packaging.version import Version


class ManifestPlist:
    NAME = 'Manifest.plist'

    def __init__(self, plist_data):
        self._plist_data = plist_data

    @staticmethod
    def from_path(path: Path):
        """
        Create a manifest plist from a Manifest.plist path.
        :param path: Path to Manifest.plist file.
        :return: ManifestPlist object:
        :rtype: ManifestPlist
        """
        return ManifestPlist(plistlib.loads(path.read_bytes()))

    @property
    def is_encrypted(self) -> bool:
        return self._plist_data['IsEncrypted']

    @property
    def keybag(self) -> bytes:
        return self._plist_data['BackupKeyBag']

    @property
    def manifest_key(self) -> bytes:
        return self._plist_data['ManifestKey']

    @property
    def product_version(self) -> Version:
        return Version(self._plist_data['Lockdown']['ProductVersion'])
