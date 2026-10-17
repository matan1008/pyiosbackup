import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from bytestruct import U8, U16_BE, BinaryDataError, BinaryParseError, BinaryStruct, ByteReader, Bytes, CodecBase, \
    Const, PrefixedArray, u8, u16, u32, u64

from pyiosbackup.exceptions import MissingEntryError
from pyiosbackup.manifest_dbs.manifest_db_interface import ManifestDb

NULL_LENGTH = 0xffff


class MbdbBytes(CodecBase[bytes]):
    """ A big-endian u16 length and that many bytes; a length of 0xffff stands for an empty value. """

    def read(self, reader: ByteReader) -> bytes:
        length = U16_BE.read(reader)
        if length == NULL_LENGTH:
            return b''
        return reader.read(length)

    def build(self, value: bytes) -> bytes:
        if not value:
            return U16_BE.build(NULL_LENGTH)
        return U16_BE.build(len(value)) + value


MBDB_BYTES = MbdbBytes()


class MbdbString(CodecBase[str]):
    """ An MbdbBytes value holding a NUL-padded UTF-8 string. """

    def read(self, reader: ByteReader) -> str:
        offset = reader.absolute
        try:
            return MBDB_BYTES.read(reader).rstrip(b'\x00').decode()
        except UnicodeDecodeError as e:
            raise BinaryParseError(f'invalid UTF-8: {e}', offset=offset) from e

    def build(self, value: str) -> bytes:
        return MBDB_BYTES.build(value.encode())


MBDB_STRING = MbdbString()


@dataclass
class MbdbHeader(BinaryStruct):
    magic: Annotated[bytes, Bytes(4), Const(b'mbdb')] = field(default=b'mbdb', init=False)
    version: Annotated[bytes, Bytes(2), Const(b'\x05\x00')] = field(default=b'\x05\x00', init=False)


@dataclass
class MbdbProperty(BinaryStruct):
    name: Annotated[str, MBDB_STRING]
    value: Annotated[str, MBDB_STRING]


@dataclass
class MbdbStat(BinaryStruct, byte_order='>'):
    mode: u16
    unknown2: u32
    unknown3: u32
    user_id: u32
    group_id: u32
    mtime: u32
    atime: u32
    ctime: u32
    size: u64
    flags: u8


@dataclass
class MbdbRecord(BinaryStruct):
    domain: Annotated[str, MBDB_STRING]
    filename: Annotated[str, MBDB_STRING]
    linktarget: Annotated[str, MBDB_STRING]
    data_hash: Annotated[bytes, MBDB_BYTES]
    encryption_key: Annotated[bytes, MBDB_BYTES]
    stat: Annotated[MbdbStat, MbdbStat]
    properties: Annotated[list[MbdbProperty], PrefixedArray(U8, MbdbProperty)]


def parse_mbdb(data: bytes) -> list[MbdbRecord]:
    """
    Parse a Manifest.mbdb file, stopping at the first record that doesn't parse (trailing bytes are ignored).
    :param data: Raw Manifest.mbdb.
    :return: Manifest records.
    """
    reader = ByteReader(data)
    MbdbHeader.read(reader)
    records = []
    while reader.remaining:
        try:
            records.append(MbdbRecord.read(reader))
        except BinaryDataError:
            break
    return records


class ManifestDbMbdb(ManifestDb):
    NAME = 'Manifest.mbdb'

    def __init__(self, path, records):
        super().__init__(path)
        self.records = records

    @classmethod
    def from_path(cls, path: Path, manifest, keybag):
        records = []
        for record in parse_mbdb(path.read_bytes()):
            stat = record.stat
            records.append({
                'file_id': hashlib.sha1(f'{record.domain}-{record.filename}'.encode()).hexdigest(),
                'domain': record.domain,
                'relative_path': record.filename,
                'last_modified': datetime.fromtimestamp(stat.mtime, timezone.utc),
                'created': datetime.fromtimestamp(stat.ctime, timezone.utc),
                'last_status_change': datetime.fromtimestamp(stat.atime, timezone.utc),
                'size': stat.size,
                'mode': stat.mode,
                'group_id': stat.group_id,
                'user_id': stat.user_id,
                'encryption_key': record.encryption_key,
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
