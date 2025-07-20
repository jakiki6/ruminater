import uuid
import xml.etree.ElementTree as ET


def _xml_to_dict(elem):
    return {
        "tag": elem.tag,
        "attributes": elem.attrib or {},
        "text": (elem.text or "").strip(),
        "children": [_xml_to_dict(child) for child in elem],
    }


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
    return str(uuid.UUID(bytes=blob))
