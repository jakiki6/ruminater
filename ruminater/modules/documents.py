from . import mappings, chew
from .. import module

import zipfile
import xml.etree.ElementTree as ET

class DocxModule(module.RuminaterModule):
    def chew(self):
        zf = zipfile.ZipFile(self.blob, "r")
        meta = {}
        meta["type"] = "docx"

        try:
            with zf.open("docProps/core.xml", "r") as f:
                root = ET.fromstring(f.read())

            for child in root:
                match child.tag:
                    case "{http://purl.org/dc/elements/1.1/}creator":
                        meta["creator"] = child.text
                    case "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastModifiedBy":
                        meta["last-modified-by"] = child.text
                    case "{http://purl.org/dc/terms/}created":
                        meta["created"] = child.text
                    case "{http://purl.org/dc/terms/}modified":
                        meta["modified"] = child.text
                    case "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastPrinted":
                        meta["last-printed"] = child.text
                    case "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}revision":
                        meta["revision"] = int(child.text)
        except:
            pass

        try:
            with zf.open("docProps/app.xml", "r") as f:
                root = ET.fromstring(f.read())

            for child in root:
                match child.tag:
                    case "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Application":
                        meta["application"] = child.text
                    case "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Pages":
                        meta["pages"] = int(child.text)
        except:
            pass

        return meta

mappings["Microsoft Word 2007+"] = DocxModule
