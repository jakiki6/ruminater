from . import chew
from .. import module
from ..buf import Buf

import zipfile
import xml.etree.ElementTree as ET
import re
from io import BufferedReader

@module.register
class DocxModule(module.RuminaterModule):
    def identify(buf):
        return False # TODO

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

@module.register
class PdfModule(module.RuminaterModule):
    obj_regex = re.compile(r"^(\d+)\s+(\d+)\s+obj.*$")
    TOKEN_PATTERN = re.compile(r"( << | >> | \[ | \] | /[^\s<>/\[\]()]+ | \d+\s+\d+\s+R | \d+\.\d+ | \d+ | \( (?: [^\\\)] | \\ . )* \) | <[0-9A-Fa-f]*> | true | false | null )", re.VERBOSE | re.DOTALL)

    def identify(buf):
        return buf.peek(5) == b"%PDF-"

    def chew(self):
        self.buf = Buf(BufferedReader(self.buf))

        meta = {}
        meta["type"] = "pdf"

        meta["version"] = self.buf.readline()[:-1].decode("latin-1").split("-")[1]
        meta["binary_comment"] = self.buf.readline()[:-1].hex()

        meta["objects"] = []
        while True:
            line = self.buf.readline()[:-1].decode("latin-1")
            if len(line) == 0:
                continue

            match = self.obj_regex.search(line)
            if match:
                obj_id = int(match.group(1))
                obj_gen = int(match.group(2))
                d = self.read_dict()
                self.buf.readline()

                meta["objects"].append({
                    "id": obj_id,
                    "generation": obj_gen,
                    "dictionary": d
                })

                if "Length" in d:
                    self.buf.readline()
                    self.buf.skip(d["Length"])
                    self.buf.readline()
                    self.buf.readline()

                while self.buf.peek(1) in (b" ", b"\n"):
                    self.buf.skip(1)

                self.buf.skip(6)

                while self.buf.peek(1) in (b" ", b"\n"):
                    self.buf.skip(1)
            else:
                break

        if self.buf.peek(1) == b"0":
            xref_count = int(self.buf.readline().decode("latin-1").split(" ")[1].split("\n")[0])

            meta["xref_count"] = xref_count
            meta["xrefs"] = []
            for i in range(0, xref_count):
                line = self.buf.readline()[:-1].decode("latin-1").split(" ")

                meta["xrefs"].append({
                    "offset": int(line[0]),
                    "generation": int(line[1]),
                    "in-use": line[2] == "n"
                })

            self.buf.readline()

        meta["trailer"] = self.read_dict()

        return meta

    def read_dict(self):
        while self.buf.peek(2) != b"<<":
            self.buf.skip(1)

        d = self.buf.read(2)
        level = 1

        while level:
            if self.buf.peek(2) == b"<<":
                level += 1
                d += self.buf.read(1)
            elif self.buf.peek(2) == b">>":
                level -= 1
                d += self.buf.read(1)

            d += self.buf.read(1)

        return self.process_dict(d.decode("latin-1"))

    @classmethod
    def process_dict(cls, d):
        return cls.parse(cls.tokenize(d))

    @classmethod
    def tokenize(cls, s):
        for match in cls.TOKEN_PATTERN.finditer(s):
            yield match.group(0)

    @classmethod
    def parse(cls, tokens):
        token = next(tokens, None)
        if token != "<<":
            raise ValueError("Dictionary must start with <<")
        return cls.parse_dict(tokens)

    @classmethod
    def parse_dict(cls, tokens):
        result = {}
        key = None
        for token in tokens:
            if token == ">>":
                return result
            if key is None:
                if not token.startswith("/"):
                    raise ValueError(f"Expected key starting with /, got {token}")
                key = token[1:]
            else:
                value = cls.parse_value(token, tokens)
                result[key] = value
                key = None
        raise ValueError("Unterminated dictionary")

    @classmethod
    def parse_array(cls, tokens):
        result = []
        for token in tokens:
            if token == "]":
                return result
            result.append(cls.parse_value(token, tokens))
        raise ValueError("Unterminated array")

    @classmethod
    def parse_value(cls, token, tokens):
        if token == "<<":
            return cls.parse_dict(tokens)
        elif token == "[":
            return cls.parse_array(tokens)
        elif re.match(r"\d+\s+\d+\s+R", token):
            return token.strip()
        elif token in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[token]
        elif re.match(r"\d+\.\d+", token):
            return float(token)
        elif token.isdigit():
            return int(token)
        elif token.startswith("("):
            token = token[1:-1]
            if len(token) >= 2 and token[0] == "\xfe" and token[1] == "\xff":
                token = token.encode("latin-1").decode("utf-16")

            return token.replace("\\(", "(").replace("\\)", ")")
        elif token.startswith("<"):
            return bytes.fromhex(token[1:-1]).hex()
        elif token.startswith("/"):
            return token
        else:
            raise ValueError(f"Unknown token: {token}")
