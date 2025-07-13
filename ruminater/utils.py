import xml.etree.ElementTree as ET

def _xml_to_dict(elem):
    return {
        "tag": elem.tag,
        "attributes": elem.attrib or {},
        "text": (elem.text or "").strip(),
        "children": [_xml_to_dict(child) for child in elem]
    }

def xml_to_dict(string):
    return _xml_to_dict(ET.fromstring(string))
