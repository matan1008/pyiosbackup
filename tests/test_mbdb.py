import pytest
from bytestruct import UnexpectedConstantError

from pyiosbackup.manifest_dbs.mbdb import MbdbProperty, MbdbRecord, MbdbStat, parse_mbdb

RECORD = MbdbRecord(
    domain='HomeDomain',
    filename='Library/Preferences/com.apple.test.plist',
    linktarget='',
    data_hash=20 * b'\x11',
    encryption_key=b'\x02\x00\x00\x00' + 40 * b'\x22',
    stat=MbdbStat(mode=0o100644, unknown2=1, unknown3=2, user_id=501, group_id=501, mtime=1628082463,
                  atime=1628082509, ctime=1627974948, size=9, flags=0),
    properties=[MbdbProperty('com.apple.name', 'value')],
)


def test_parsing_record():
    data = (
        b'mbdb\x05\x00'
        b'\x00\x0aHomeDomain'
        b'\x00\x28Library/Preferences/com.apple.test.plist'
        b'\xff\xff'  # No link target
        b'\x00\x14' + 20 * b'\x11' +
        b'\x00\x2c\x02\x00\x00\x00' + 40 * b'\x22' +
        b'\x81\xa4'  # Mode
        b'\x00\x00\x00\x01\x00\x00\x00\x02'  # Unknown
        b'\x00\x00\x01\xf5\x00\x00\x01\xf5'  # User and group
        b'\x61\x0a\x91\x1f\x61\x0a\x91\x4d\x61\x08\xed\x24'  # Times
        b'\x00\x00\x00\x00\x00\x00\x00\x09'  # Size
        b'\x00'  # Flags
        b'\x01'  # Properties count
        b'\x00\x0ecom.apple.name\x00\x05value'
    )
    assert parse_mbdb(data) == [RECORD]


def test_parsing_padded_and_empty_strings():
    record = MbdbRecord.parse(b'\x00\x05abc\x00\x00' + b'\x00\x00' + 4 * b'\xff\xff' + MbdbStat.SIZE * b'\x00' + b'\x00')
    assert (record.domain, record.filename, record.linktarget) == ('abc', '', '')
    assert (record.data_hash, record.encryption_key) == (b'', b'')


def test_building_record():
    assert parse_mbdb(b'mbdb\x05\x00' + RECORD.build() + RECORD.build()) == [RECORD, RECORD]


def test_parsing_stops_at_truncated_record():
    data = b'mbdb\x05\x00' + RECORD.build()
    assert parse_mbdb(data + data[6:-1]) == [RECORD]
    assert parse_mbdb(b'mbdb\x05\x00') == []


def test_parsing_bad_header():
    with pytest.raises(UnexpectedConstantError):
        parse_mbdb(b'mbdb\x04\x00' + RECORD.build())
