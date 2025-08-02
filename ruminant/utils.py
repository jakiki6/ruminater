import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import zlib


def _xml_to_dict(elem):
    res = {}

    if elem.tag:
        res["tag"] = elem.tag

    if elem.attrib:
        res["attributes"] = elem.attrib

    if elem.text and len(elem.text.strip()):
        res["text"] = elem.text

    children = list(elem)
    if len(children):
        res["children"] = [_xml_to_dict(child) for child in children]

    return res


def xml_to_dict(string):
    while len(string):
        try:
            return _xml_to_dict(ET.fromstring(string))
        except ET.ParseError:
            string = string[:-1]

    return {}


def read_varint(buf):
    i = 0
    o = 0
    c = 0x80
    while c & 0x80:
        c = buf.read(1)[0]
        i |= (c & 0x7f) << o
        o += 7

    return i


def read_protobuf(buf, length):
    buf.pushunit()
    buf.setunit(length)

    entries = []
    while buf.unit > 0:
        entry_id = read_varint(buf)
        entry_type = entry_id & 0b111
        entry_id >>= 3

        match entry_type:
            case 0:
                value = read_varint(buf)
            case 1:
                value = buf.ru64l()
            case 2:
                value_length = read_varint(buf)
                value = buf.read(value_length)
            case 5:
                value = buf.ru32l()
            case _:
                break

        entries.append([entry_id, entry_type, value])

    buf.skipunit()
    buf.popunit()

    return entries


def to_uuid(blob):
    try:
        return str(uuid.UUID(bytes=blob))
    except ValueError:
        return blob.hex()


def mp4_time_to_iso(mp4_time):
    mp4_epoch = datetime(1904, 1, 1, tzinfo=timezone.utc)
    dt = mp4_epoch + timedelta(seconds=mp4_time)
    return dt.isoformat()


def stream_deflate(src, dst, compressed_size, chunk_size=1 << 24):
    remaining = compressed_size
    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)

    while remaining > 0:
        chunk = src.read(min(chunk_size, remaining))
        dst.write(decompressor.decompress(chunk))
        remaining -= len(chunk)

    flushed = decompressor.flush()
    if flushed:
        dst.write(flushed)
