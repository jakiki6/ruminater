from .. import module, utils
from . import chew
from ..buf import Buf

import zipfile
import xml.etree.ElementTree as ET
import re
import zlib
import math


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


def png_decode(data, columns, rowlength):
    # based on https://github.com/py-pdf/pypdf/blob/47a7f8fae02aa06585f8c8338dcab647e2547917/pypdf/filters.py#L204  # noqa: E501
    # licensed under BSD-3
    # see https://github.com/py-pdf/pypdf/blob/47a7f8fae02aa06585f8c8338dcab647e2547917/LICENSE for attribution  # noqa: E501

    output = b""
    prev_rowdata = bytes(rowlength)
    bpp = (rowlength - 1) // columns
    for row in range(0, len(data), rowlength):
        rowdata = bytearray(data[row:row + rowlength])
        cmd = rowdata[0]

        match cmd:
            case 0:
                pass
            case 1:
                for i in range(bpp + 1, rowlength):
                    rowdata[i] = (rowdata[i] + rowdata[i - bpp]) % 256
            case 2:
                for i in range(1, rowlength):
                    rowdata[i] = (rowdata[i] + prev_rowdata[i]) % 256
            case 3:
                for i in range(1, bpp + 1):
                    floor = prev_rowdata[i] // 2
                    rowdata[i] = (rowdata[i] + floor) % 256
                for i in range(bpp + 1, rowlength):
                    left = rowdata[i - bpp]
                    floor = (left + prev_rowdata[i]) // 2
                    rowdata[i] = (rowdata[i] + floor) % 256
            case 4:
                for i in range(1, bpp + 1):
                    up = prev_rowdata[i]
                    paeth = up
                    rowdata[i] = (rowdata[i] + paeth) % 256
                for i in range(bpp + 1, rowlength):
                    left = rowdata[i - bpp]
                    up = prev_rowdata[i]
                    up_left = prev_rowdata[i - bpp]
                    p = left + up - up_left
                    dist_left = abs(p - left)
                    dist_up = abs(p - up)
                    dist_up_left = abs(p - up_left)
                    if dist_left <= dist_up and dist_left <= dist_up_left:
                        paeth = left
                    elif dist_up <= dist_up_left:
                        paeth = up
                    else:
                        paeth = up_left
                    rowdata[i] = (rowdata[i] + paeth) % 256
            case _:
                raise ValueError(f"Unsupported PNG predictor {cmd}")

        prev_rowdata = bytes(rowdata)
        output += rowdata[1:]

    return output


class ReparsePoint(Exception):
    pass


@module.register
class PdfModule(module.RuminantModule):
    TOKEN_PATTERN = re.compile(
        r"( \s | << | >> | \[ | \] | /[^\s<>/\[\]()]+ | \d+\s+\d+\s+R | \d+\.\d+ | \d+ | \( (?: [^\\\)] | \\ . )* \) | <[0-9A-Fa-f\s]*> | true | false | null )",  # noqa: E501
        re.VERBOSE | re.DOTALL,
    )
    INDIRECT_OBJECT_PATTERN = re.compile(r"^(\d+) (\d+) R$")
    XREF_PATTERN = re.compile(r"^(\d{10}) (\d{5}) ([nf]).*$")

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

        self.objects = {}
        self.queue = []
        self.compressed = []

        ver_15_offsets = []

        if self.buf.peek(4) == b"xref":
            self.buf.rl()

            obj_id = 0
            while True:
                line = self.buf.rl().decode("latin-1")

                if "trailer" in line:
                    d = self.read_value(self.buf)

                    if "XRefStm" in d:
                        ver_15_offsets.append(d["XRefStm"])

                    if "Prev" in d:
                        self.buf.seek(d["Prev"])
                        self.buf.rl()
                        continue

                    break

                m = self.XREF_PATTERN.match(line)
                if m:
                    if m.group(3) == "n":
                        self.queue.append((int(m.group(1)), self.buf))

                    obj_id += 1
                else:
                    obj_id = int(line.split(" ")[0])
        else:
            # version 1.5+
            ver_15_offsets.append(self.buf.tell())

        for offset in ver_15_offsets:
            self.buf.seek(offset)
            self.parse_object(self.buf)

        while len(self.queue) + len(self.compressed):
            stuck = True
            if len(self.compressed):
                for compressed_id, compressed_index, compressed_buf in self.compressed[:]:  # noqa: E501
                    if compressed_id in self.objects:
                        try:
                            with compressed_buf:
                                compressed_buf.seek(
                                    self.objects[compressed_id][0]["offset"])
                                self.parse_object(compressed_buf,
                                                  packed=(compressed_index,
                                                          compressed_id))
                            self.compressed.remove(
                                (compressed_id, compressed_index,
                                 compressed_buf))
                            stuck = False
                        except ReparsePoint:
                            pass

            if len(self.queue):
                for i in range(0, len(self.queue)):
                    try:
                        offset, buf = self.queue[0]

                        with buf:
                            buf.seek(offset)
                            self.parse_object(self.buf)

                        self.queue.pop(0)
                        stuck = False
                        break
                    except ReparsePoint:
                        self.queue.append(self.queue.pop(0))

            if stuck:
                break

        for k in list(self.objects.keys()):
            if len(self.objects[k]) == 0:
                del self.objects[k]

        meta["objects"] = self.objects

        self.buf.skip(self.buf.available())

        return meta

    def resolve(self, value):
        if isinstance(value, str):
            m = self.INDIRECT_OBJECT_PATTERN.match(value)

            if m:
                obj_id, obj_gen = int(m.group(1)), int(m.group(2))

                if obj_id not in self.objects or obj_gen not in self.objects[
                        obj_id]:
                    raise ReparsePoint()

                return self.objects[obj_id][obj_gen]["value"]

        return value

    def parse_object(self, buf, packed=None, obj_id=None):
        obj = {}
        obj["offset"] = buf.tell()

        if obj_id is None:
            line = buf.rl().decode("latin-1")
            obj_id, obj_generation, _ = line.split(" ")
        else:
            obj_generation = 0

        obj_id = int(obj_id)
        obj_generation = int(obj_generation)

        if packed is None:
            if obj_id not in self.objects:
                self.objects[obj_id] = {}

            if obj_generation in self.objects[obj_id]:
                return

        obj["value"] = self.read_value(buf)

        if isinstance(obj["value"], dict):
            if "Length" in obj["value"]:
                length = self.resolve(obj["value"]["Length"])

                if not buf.rl().endswith(b"stream"):
                    buf.rl()

                with buf.sub(length):
                    old_buf = buf

                    filters = self.resolve(obj["value"].get("Filter", []))
                    if isinstance(filters, str):
                        filters = [filters]

                    for filt in filters:
                        match filt:
                            case "/FlateDecode":
                                buf = Buf(zlib.decompress(buf.read()))

                    if "DecodeParms" in obj["value"]:
                        params = self.resolve(obj["value"]["DecodeParms"])

                        if "Predictor" in params:
                            match params["Predictor"]:
                                case 0:
                                    pass
                                case 10 | 11 | 12 | 13 | 14 | 15:
                                    buf = Buf(
                                        png_decode(
                                            buf.read(), params["Columns"],
                                            math.ceil(
                                                params["Columns"] *
                                                params.get("Colors", 1) *
                                                params.get(
                                                    "BitsPerComponent", 8) / 8)
                                            + 1))
                                case _:
                                    raise ValueError(
                                        f"Unknown predictor: {params['Predictor']}"  # noqa: E501
                                    )

                    if packed is not None:
                        buf.seek(
                            self.resolve(obj["value"].get("First", 0)) +
                            packed[0])
                        return self.parse_object(buf, obj_id=packed[1])

                    obj_type = self.resolve(obj["value"].get("Type"))
                    obj_subtype = self.resolve(obj["value"].get("Subtype"))

                    match obj_type, obj_subtype:
                        case "/Metadata", "/XML":
                            obj["data"] = utils.xml_to_dict(buf.read())
                        case "/XRef", _:
                            w0, w1, w2 = self.resolve(obj["value"]["W"])
                            index = self.resolve(obj["value"].get("Index", []))
                            if len(index) == 0:
                                index = [0, (1 << 64) - 1]

                            while buf.available():
                                f0 = int.from_bytes(buf.read(w0),
                                                    "big") if w0 else 1
                                f1 = int.from_bytes(buf.read(w1), "big")
                                f2 = int.from_bytes(buf.read(w2),
                                                    "big") if w2 else 0

                                if f0 == 1:
                                    self.queue.append((f1, old_buf))
                                    index[0] += 1
                                    index[1] -= 1

                                    if index[1] <= 0:
                                        index.pop(0)
                                        index.pop(0)
                                elif f0 == 2 and (f1 | f2):
                                    self.compressed.append((f1, f2, old_buf))

                            if "Prev" in obj["value"]:
                                self.queue.append(
                                    (self.resolve(obj["value"]["Prev"]),
                                     old_buf))
                        case _, _:
                            obj["data"] = chew(buf)

                    buf = old_buf

        if packed is None:
            self.objects[obj_id][obj_generation] = obj

        return obj

    def read_value(self, buf):
        d = b""
        level = 0

        while True:
            if buf.peek(6) == b"endobj":
                break

            if buf.peek(2) == b"<<":
                level += 1
                d += buf.read(1)
            elif buf.peek(2) == b">>":
                level -= 1
                d += buf.read(1)

                if level == 0:
                    d += buf.read(1)
                    break

            d += buf.read(1)

        value = self.parse_value(list(self.tokenize(d.decode("latin-1"))))
        return value

    @classmethod
    def tokenize(cls, s):
        for match in cls.TOKEN_PATTERN.finditer(s):
            if match.group(0) not in ("\r", "\n", " "):
                yield match.group(0)

    @classmethod
    def parse_dict(cls, tokens):
        result = {}
        key = None
        while len(tokens):
            if tokens[0] == ">>":
                tokens.pop(0)
                return result
            if key is None:
                if not tokens[0].startswith("/"):
                    raise ValueError(
                        f"Expected key starting with /, got {tokens[0]}")
                key = tokens.pop(0)[1:]
            else:
                value = cls.parse_value(tokens)
                result[key] = value
                key = None
        raise ValueError("Unterminated dictionary")

    @classmethod
    def parse_array(cls, tokens):
        result = []
        while len(tokens):
            if tokens[0] == "]":
                tokens.pop(0)
                return result
            result.append(cls.parse_value(tokens))
        raise ValueError("Unterminated array")

    @classmethod
    def parse_value(cls, tokens):
        token = tokens.pop(0)

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
            return bytes.fromhex(token[1:-1].replace(" ", "")).hex()
        elif token.startswith("/"):
            return token
        else:
            raise ValueError(f"Unknown token: {token}")
