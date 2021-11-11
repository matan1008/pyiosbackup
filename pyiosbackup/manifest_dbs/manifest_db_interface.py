from abc import ABC, abstractmethod
from pathlib import Path


class ManifestDb(ABC):
    NAME = ''

    def __init__(self, path):
        self.path = path

    @classmethod
    @abstractmethod
    def from_path(cls, path: Path, manifest, keybag):
        pass

    @abstractmethod
    def get_metadata_by_id(self, file_id: str):
        pass

    @abstractmethod
    def get_metadata_by_domain_and_path(self, domain: str, relative_path: str):
        pass

    @abstractmethod
    def get_all_entries(self):
        pass
