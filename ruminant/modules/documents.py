from .. import module
from ..buf import Buf

import zipfile
import xml.etree.ElementTree as ET
import re
from io import BufferedReader


@module.register
class DocxModule(module.RuminantModule):

    def identify(buf):
        return False  # TODO

    def chew(self):
        zf = zipfile.ZipFile(self.buf, "r")
        meta = {}
        meta["type"] = "docx"

        try:
            with zf.open("docProps/core.xml", "r") as f:
                root = ET.fromstring(f.read())

            for child in root:
                match child.tag:
                    case "{http://purl.org/dc/elements/1.1/}creator":
                        meta["creator"] = child.text
                    case "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastModifiedBy":  # noqa: E501
                        meta["last-modified-by"] = child.text
                    case "{http://purl.org/dc/terms/}created":
                        meta["created"] = child.text
                    case "{http://purl.org/dc/terms/}modified":
                        meta["modified"] = child.text
                    case "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastPrinted":  # noqa: E501
                        meta["last-printed"] = child.text
                    case "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}revision":  # noqa: E501
                        meta["revision"] = int(child.text)
        except ET.ParseError:
            pass

        try:
            with zf.open("docProps/app.xml", "r") as f:
                root = ET.fromstring(f.read())

            for child in root:
                match child.tag:
                    case "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Application":  # noqa: E501
                        meta["application"] = child.text
                    case "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Pages":  # noqa: E501
                        meta["pages"] = int(child.text)
        except ET.ParseError:
            pass

        return meta


@module.register
class PdfModule(module.RuminantModule):
    def identify(buf):
        return buf.peek(5) == b"%PDF-"

    def chew(self):
        self.buf = Buf(BufferedReader(self.buf))

        meta = {}
        meta["type"] = "pdf"

        meta["version"] = (
            self.buf.readline()[:-1].decode("latin-1").split("-")[1])
        meta["binary_comment"] = self.buf.readline()[:-1].hex()

        return meta
