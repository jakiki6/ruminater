from .. import module

import zipfile
import xml.etree.ElementTree as ET
import re


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
    TOKEN_PATTERN = re.compile(
        r"( << | >> | \[ | \] | /[^\s<>/\[\]()]+ | \d+\s+\d+\s+R | \d+\.\d+ | \d+ | \( (?: [^\\\)] | \\ . )* \) | <[0-9A-Fa-f]*> | true | false | null )",  # noqa: E501
        re.VERBOSE | re.DOTALL,
    )

    def identify(buf):
        return buf.peek(5) == b"%PDF-"

    def chew(self):
        meta = {}
        meta["type"] = "pdf"

        meta["version"] = (self.buf.rl().decode("latin-1").split("-")[1])
        meta["binary_comment"] = self.buf.rl().hex()

        self.buf.seek(0, 2)
        while self.buf.peek(9) != b"startxref":
            self.buf.seek(-1, 1)

        self.buf.rl()
        xref_offset = int(self.buf.rl().decode("latin-1"))
        meta["xref-offset"] = xref_offset

        self.buf.seek(xref_offset)
        meta["objects"] = []
        if self.buf.peek(4) == b"xref":
            self.buf.rl()

            xref_pattern = re.compile(r"^(\d{10}) (\d{5}) ([nf])$")

            obj_id = 0
            while True:
                line = self.buf.rl().decode("latin-1")

                if line == "trailer":
                    break

                m = xref_pattern.match(line)
                if m:
                    with self.buf:
                        self.buf.seek(int(m.group(1)))
                        meta["objects"].append(
                            {
                                "offset": int(m.group(1)),
                                "in-use": m.group(3) == "n"
                            } | {"data": self.parse_object(self.buf)} if m.
                            group(3) == "n" else {})

                    obj_id += 1
                else:
                    obj_id = int(line.split(" ")[0])
        else:
            # version 1.5+
            meta["objects"] = self.parse_object(self.buf)

        self.buf.skip(self.buf.available())

        return meta

    def parse_object(self, buf):
        obj = {}
        obj_id, obj_generation, _ = buf.rl().decode("latin-1").split(" ")
        obj["id"] = int(obj_id)
        obj["generation"] = int(obj_generation)

        obj["dict"] = self.read_dict(buf)

        return obj

    def read_dict(self, buf):
        while buf.peek(2) != b"<<":
            buf.skip(1)

        d = buf.read(2)
        level = 1

        while level:
            if buf.peek(2) == b"<<":
                level += 1
                d += buf.read(1)
            elif buf.peek(2) == b">>":
                level -= 1
                d += buf.read(1)

            d += buf.read(1)

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
                    raise ValueError(
                        f"Expected key starting with /, got {token}")
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
