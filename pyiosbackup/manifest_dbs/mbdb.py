from pathlib import Path
from datetime import timezone, datetime
import hashlib

from construct import Struct, Const, Bytes, GreedyRange, Int16ub, IfThenElse, Computed, this, \
    Int32ub, Int64ub, Byte, Array, PaddedString

from pyiosbackup.exceptions import MissingEntryError
from pyiosbackup.manifest_dbs.manifest_db_interface import ManifestDb

mbdb_struct = Struct(
    Const(b'mbdb', Bytes(4)),
    'version' / Const(b'\x05\x00', Bytes(2)),
    'records' / GreedyRange(Struct(
        'domain_len' / Int16ub,
        'domain' / IfThenElse(this.domain_len != 0xffff, PaddedString(this.domain_len, 'utf8'), Computed('')),
        'filename_len' / Int16ub,
        'filename' / IfThenElse(this.filename_len != 0xffff, PaddedString(this.filename_len, 'utf8'), Computed('')),
        'link_len' / Int16ub,
        'linktarget' / IfThenElse(this.link_len != 0xffff, PaddedString(this.link_len, 'utf8'), Computed('')),
        'hash_len' / Int16ub,
        'data_hash' / IfThenElse(this.hash_len != 0xffff, Bytes(this.hash_len), Computed(b'')),
        'key_length' / Int16ub,
        'encryption_key' / IfThenElse(this.key_length != 0xffff, Bytes(this.key_length), Computed(b'')),
        'mode' / Int16ub,
        'unknown2' / Int32ub,
        'unknown3' / Int32ub,
        'user_id' / Int32ub,
        'group_id' / Int32ub,
        'mtime' / Int32ub,
        'atime' / Int32ub,
        'ctime' / Int32ub,
        'size' / Int64ub,
        'flags' / Byte,
        'properties_count' / Byte,
        'properties' / Array(this.properties_count, Struct(
            'name_len' / Int16ub,
            'name' / IfThenElse(this.name_len != 0xffff, PaddedString(this.name_len, 'utf8'), Computed('')),
            'value_len' / Int16ub,
            'value' / IfThenElse(this.value_len != 0xffff, PaddedString(this.value_len, 'utf8'), Computed('')),
        )),
    ))
)


class ManifestDbMbdb(ManifestDb):
    NAME = 'Manifest.mbdb'

    def __init__(self, path, records):
        super().__init__(path)
        self.records = records

    @classmethod
    def from_path(cls, path: Path, manifest, keybag):
        mbdb = mbdb_struct.parse(path.read_bytes())
        records = []
        for record in mbdb.records:
            domain = record['domain']
            filename = record['filename']
            records.append({
                'file_id': hashlib.sha1(f'{domain}-{filename}'.encode()).hexdigest(),
                'domain': domain,
                'relative_path': filename,
                'last_modified': datetime.fromtimestamp(record['mtime'], timezone.utc),
                'created': datetime.fromtimestamp(record['ctime'], timezone.utc),
                'last_status_change': datetime.fromtimestamp(record['atime'], timezone.utc),
                'size': record['size'],
                'mode': record['mode'],
                'group_id': record['group_id'],
                'user_id': record['user_id'],
                'encryption_key': record['encryption_key'],
            })
        return ManifestDbMbdb(path, records)

    def get_metadata_by_id(self, file_id: str):
        for record in self.records:
            if record['file_id'] == file_id:
                return record
        raise MissingEntryError()

    def get_metadata_by_domain_and_path(self, domain: str, relative_path: str):
        for record in self.records:
            if record['domain'] == domain and record['relative_path'] == relative_path:
                return record
        raise MissingEntryError()

    def get_all_entries(self):
        return self.records
