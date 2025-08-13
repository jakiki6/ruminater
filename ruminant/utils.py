from .oids import OIDS
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import zlib
import bz2


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


def stream_bzip2(src, dst, compressed_size, chunk_size=1 << 24):
    remaining = compressed_size
    decompressor = bz2.BZ2Decompressor()

    while remaining > 0:
        chunk = src.read(min(chunk_size, remaining))
        dst.write(decompressor.decompress(chunk))
        remaining -= len(chunk)

    src.seek(-len(decompressor.unused_data), 1)


def read_der(buf):
    data = {}

    tag = buf.ru8()
    constructed = bool((tag >> 5) & 0x01)

    if tag & 0x0f == 0x0f:
        c = 0x80
        while c & 0x80:
            c = buf.ru8()
            tag <<= 7
            tag |= c & 0x7f

    length = buf.ru8()
    if length & 0x80:
        length = int.from_bytes(buf.read(length & 0x7f), "big")

    buf.pushunit()
    buf.setunit(length)

    data["type"] = None
    data["length"] = length

    match tag:
        case 0x01:
            data["type"] = "BOOLEAN"
            data["value"] = bool(buf.ru8())
        case 0x02 | 0x0a:
            data["type"] = ["INTEGER", "ENUMERATED"][tag >> 3]
            data["value"] = int.from_bytes(buf.readunit(), "big", signed=True)
        case 0x03:
            data["type"] = "BIT STRING"
            skip = buf.ru8()
            data["value"] = bin(
                int.from_bytes(buf.readunit()) >> skip)[2:].zfill(length * 8 -
                                                                  skip)
        case 0x04:
            data["type"] = "OCTET STRING"

            nested = True
            with buf:
                try:
                    if buf.ru8() & 0x0f == 0x0f:
                        c = 0x80
                        while c & 0x80:
                            c = buf.ru8()

                    length = buf.ru8()
                    if length & 0x80:
                        length = int.from_bytes(buf.read(length & 0x7f), "big")

                    assert buf.unit == length
                except Exception:
                    nested = False

            if nested:
                with buf.subunit():
                    data["value"] = read_der(buf)
            else:
                data["value"] = buf.readunit().hex()
        case 0x05:
            data["type"] = "NULL"
            data["value"] = None
        case 0x06:
            data["type"] = "OBJECT IDENTIFIER"

            oid = []
            c = buf.ru8()
            oid.append(c // 40)
            oid.append(c % 40)

            i = 0
            while buf.unit > 0:
                c = buf.ru8()
                i <<= 7
                i |= c & 0x7f

                if not c & 0x80:
                    oid.append(i)
                    i = 0

            data["value"] = lookup_oid(oid)
        case 0x0c:
            data["type"] = "UTF8String"
            data["value"] = buf.readunit().decode("utf-8")
        case 0x10 | 0x11 | 0x30 | 0x31:
            data["type"] = ["SEQUENCE", "SET"][tag & 0x01]
        case 0x13 | 0x14 | 0x16:
            data["type"] = {
                0x13: "PrintableString",
                0x14: "T61String",
                0x16: "IA5String",
            }[tag]

            data["value"] = buf.readunit().decode("ascii")
        case 0x17:
            data["type"] = "UTCTime"

            dt = datetime.strptime(buf.readunit().decode("ascii")[:-1],
                                   "%y%m%d%H%M%S")

            if dt.year < 1950:
                dt = dt.replace(year=dt.year + 100)

            data["value"] = dt.isoformat()
        case 0x18:
            data["type"] = "GeneralizedTime"

            time_string = buf.readunit().decode("ascii")[:-1]
            if '.' in time_string:
                main_time, fraction = time_string.split(".", 1)
                fraction = (fraction + "000000")[:6]
                data["value"] = datetime.strptime(
                    main_time, "%Y%m%d%H%M%S").replace(
                        microsecond=int(fraction)).isoformat(
                            timespec="microseconds") + "Z"
            else:
                data["value"] = datetime.strptime(time_string,
                                                  "%Y%m%d%H%M%S").isoformat()
        case _:
            data["type"] = f"UNKNOWN ({hex(tag)})"

    if tag >= 0x80 and tag <= 0xbe:
        data["type"] = f"X509 [{tag & 0x0f}]"

        if not constructed:
            content = buf.readunit()

            if tag & 0x0f == 0x06:
                data["value"] = content.decode("latin-1")
            else:
                data["value"] = content.hex()

    if constructed:
        data["value"] = []
        while buf.unit > 0:
            data["value"].append(read_der(buf))

    buf.skipunit()
    buf.popunit()

    return data


def lookup_oid(oid):
    data = {}
    data["raw"] = ".".join([str(x) for x in oid])

    tree = []
    root = OIDS
    for i in oid:
        if i in root:
            tree.append(root[i]["name"])
            root = root[i]["children"]
        else:
            tree.append("?")
            root = {}

    data["tree"] = tree
    if tree[-1] != "?":
        data["name"] = tree[-1]

    return data


def zlib_decompress(content):
    try:
        return zlib.decompress(content)
    except Exception:
        try:
            return zlib.decompressobj().decompress(content)
        except Exception:
            decomp = zlib.decompressobj(zlib.MAX_WBITS | 32)

            data = b""
            for c in content:
                # WHAT THE FUCK ADOBE
                try:
                    data += decomp.decompress(bytes([c]))
                except Exception:
                    pass

            return data


def decode(content, encoding="utf-8"):
    try:
        return content.decode(encoding)
    except Exception:
        return content.decode("latin-1")


def unraw(i, width, choices):
    return {"raw": i, "name": choices.get(i, "Unknown")}
