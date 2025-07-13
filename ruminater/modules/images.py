import zlib, datetime
from . import chew
from .. import module

@module.register
class IccProfileModule(module.RuminaterModule):
    def read_tag(self, offset, length):
        tag = {}

        bak = self.buf.backup()
        self.buf.seek(offset)
        typ = self.buf.read(4).decode("utf-8")
        self.buf.skip(4)
        self.buf.setunit(length - 8)

        tag["data"] = {}
        tag["data"]["type"] = typ
        match typ:
            case "text":
                tag["data"]["string"] = self.buf.readunit()[:-1].decode("ascii")
            case "desc":
                l = int.from_bytes(self.buf.read(4), "big")
                tag["data"]["string"] = self.buf.read(l - 1).decode("ascii")
            case "XYZ ":
                tag["data"]["x"] = int.from_bytes(self.buf.read(4), "big", signed=True) / 65536
                tag["data"]["y"] = int.from_bytes(self.buf.read(4), "big", signed=True) / 65536
                tag["data"]["z"] = int.from_bytes(self.buf.read(4), "big", signed=True) / 65536
            case "curv":
                tag["data"]["curve-entry-count"] = int.from_bytes(self.buf.read(4), "big")
            case "view":
                tag["data"]["illuminant"] = {
                    "x": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536,
                    "y": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536,
                    "z": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536
                }
                tag["data"]["surround"] = {
                    "x": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536,
                    "y": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536,
                    "z": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536
                }
                illuminant_type = int.from_bytes(self.buf.read(4), "big")
                tag["data"]["illuminant-type"] = {
                    "raw": illuminant_type,
                    "name": {
                        0: "Unknown",
                        1: "D50",
                        2: "D65",
                        3: "D93",
                        4: "F2",
                        5: "D55",
                        6: "A",
                        7: "Equi-Power (E)",
                        8: "F8"
                    }.get(illuminant_type, "Unknown")
                }
            case "meas":
                standard_observer = int.from_bytes(self.buf.read(4), "big")
                tag["data"]["standard-observer"] = {
                    "raw": standard_observer,
                    "name": {
                        0: "Unknown",
                        1: "CIE 1931 standard colorimetric observer",
                        2: "CIE 1964 standard colorimetric observer"
                    }.get(standard_observer, "Unknown")
                }
                tag["data"]["measurement-backing"] = { 
                    "x": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536,
                    "y": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536,
                    "z": int.from_bytes(self.buf.read(4), "big", signed=True) / 65536
                }
                measurement_geometry = int.from_bytes(self.buf.read(4), "big")
                tag["data"]["measurement-geometry"] = {
                    "raw": measurement_geometry,
                    "name": {
                        0: "Unknown",
                        1: "0°:45° or 45°:0°",
                        2: "0°:d or d:0°"
                    }.get(measurement_geometry, "Unknown")
                }
                tag["data"]["measurement-flare"] = int.from_bytes(self.buf.read(4), "big") / 65536
                standard_illuminant = int.from_bytes(self.buf.read(4), "big")
                tag["data"]["standard-illuminant"] = {
                    "raw": standard_illuminant,
                    "name": {
                        0: "Unknown",
                        1: "D50",
                        2: "D65",
                        3: "D93",
                        4: "F2",
                        5: "D55",
                        6: "A",
                        7: "Equi-Power (E)",
                        8: "F8"
                    }.get(standard_illuminant, "Unknown")
                }
            case "sig ":
                tag["data"]["signature"] = self.buf.read(4).decode("utf-8")
            case _:
                tag["data"]["unkown"] = True

        self.buf.restore(bak)

        return tag

    def identify(buf):
        return buf.peek(12) == b"ICC_PROFILE\x00"

    def chew(self):
        meta = {}
        meta["type"] = "icc-profile"
        meta["data"] = {}

        self.buf.skip(14)
        l = int.from_bytes(self.buf.read(4), "big")
        meta["data"]["length"] = l
        self.buf.setunit(l)

        meta["data"]["cmm-type"] = self.buf.read(4).decode("utf-8")
        meta["data"]["version"] = f"{self.buf.read(1)[0]}.{self.buf.read(3).hex().rstrip('0')}"
        meta["data"]["class"] = self.buf.read(4).decode("utf-8")
        meta["data"]["color-space"] = self.buf.read(4).decode("utf-8")
        meta["data"]["profile-connection-space"] = self.buf.read(4).decode("utf-8")
        meta["data"]["date"] = datetime.datetime(*[int.from_bytes(self.buf.read(2), "big") for _ in range(0, 6)]).isoformat()
        meta["data"]["file-signature"] = self.buf.read(4).decode("utf-8")
        meta["data"]["platform"] = self.buf.read(4).decode("utf-8")
        meta["data"]["flags"] = self.buf.read(4).hex()
        meta["data"]["device-manufacturer"] = self.buf.read(4).decode("utf-8")
        meta["data"]["device-model"] = self.buf.read(4).decode("utf-8")
        meta["data"]["device-attributes"] = self.buf.read(8).hex()
        render_intent = int.from_bytes(self.buf.read(4), "big")
        meta["data"]["render-intent"] = {
            "raw": render_intent,
            "name": {
                0: "Perceptual",
                1: "Relative Colorimetric",
                2: "Saturation",
                3: "Absolute Colorimetric"
            }.get(render_intent, "Unknown")
        }
        meta["data"]["pcs-illuminant"] = [int.from_bytes(self.buf.read(4), "big", signed=True) / 65536 for _ in range(0, 3)]
        meta["data"]["profile-creator"] = self.buf.read(4).decode("utf-8")
        meta["data"]["profile-id"] = self.buf.read(4).hex()
        meta["data"]["reserved"] = self.buf.read(40).hex()

        tag_count = int.from_bytes(self.buf.read(4), "big")
        meta["data"]["tag-count"] = tag_count
        meta["data"]["tags"] = []
        for i in range(0, tag_count):
            tag = {}
            tag["name"] = self.buf.read(4).decode("utf-8")
            tag["offset"] = int.from_bytes(self.buf.read(4), "big")
            tag["length"] = int.from_bytes(self.buf.read(4), "big")

            tag |= self.read_tag(tag["offset"] + 14, tag["length"])

            meta["data"]["tags"].append(tag)

        return meta

@module.register
class JpegModule(module.RuminaterModule):
    HAS_PAYLOAD = [
        0xc0,  # SOF0: Baseline DCT
        0xc1,  # SOF1: Extended sequential DCT
        0xc2,  # SOF2: Progressive DCT
        0xc3,  # SOF3: Lossless sequential
        0xc5,  # SOF5: Differential sequential DCT
        0xc6,  # SOF6: Differential progressive DCT
        0xc7,  # SOF7: Differential lossless
        0xc9,  # SOF9: Extended sequential, arithmetic coding
        0xca,  # SOF10: Progressive, arithmetic coding
        0xcb,  # SOF11: Lossless, arithmetic coding
        0xcd,  # SOF13: Differential sequential, arithmetic coding
        0xce,  # SOF14: Differential progressive, arithmetic coding
        0xcf,  # SOF15: Differential lossless, arithmetic coding
        0xc4,  # DHT: Define Huffman Table
        0xdb,  # DQT: Define Quantization Table
        0xdd,  # DRI: Define Restart Interval
        0xda,  # SOS: Start of Scan
        0xe0,  # APP0
        0xe1,  # APP1
        0xe2,  # APP2
        0xe3,  # APP3
        0xe4,  # APP4
        0xe5,  # APP5
        0xe6,  # APP6
        0xe7,  # APP7
        0xe8,  # APP8
        0xe9,  # APP9
        0xea,  # APP10
        0xeb,  # APP11
        0xec,  # APP12
        0xed,  # APP13
        0xee,  # APP14
        0xef,  # APP15
        0xfe,  # COM: Comment
        0xf0,  # JPG0 (JPEG extensions, reserved)
        0xf1,  # JPG1
        0xf2,  # JPG2
        0xf3,  # JPG3
        0xf4,  # JPG4
        0xf5,  # JPG5
        0xf6,  # JPG6
        0xf7,  # JPG7
        0xf8,  # JPG8
        0xf9,  # JPG9
        0xfa,  # JPG10
        0xfb,  # JPG11
        0xfc,  # JPG12
        0xfd,  # JPG13
    ]

    MARKER_NAME = {
        0xd8: "SOI",
        0xd9: "EOI",
        0xc0: "SOF0",
        0xc1: "SOF1",
        0xc2: "SOF2",
        0xc3: "SOF3",
        0xc5: "SOF5",
        0xc6: "SOF6",
        0xc7: "SOF7",
        0xc9: "SOF9",
        0xca: "SOF10",
        0xcb: "SOF11",
        0xcd: "SOF13",
        0xce: "SOF14",
        0xcf: "SOF15",
        0xc4: "DHT",
        0xdb: "DQT",
        0xdd: "DRI",
        0xda: "SOS",
        0xfe: "COM",
        0xe0: "APP0",
        0xe1: "APP1",
        0xe2: "APP2",
        0xe3: "APP3",
        0xe4: "APP4",
        0xe5: "APP5",
        0xe6: "APP6",
        0xe7: "APP7",
        0xe8: "APP8",
        0xe9: "APP9",
        0xea: "APP10",
        0xeb: "APP11",
        0xec: "APP12",
        0xed: "APP13",
        0xee: "APP14",
        0xef: "APP15",
        0xf0: "JPG0",
        0xf1: "JPG1",
        0xf2: "JPG2",
        0xf3: "JPG3",
        0xf4: "JPG4",
        0xf5: "JPG5",
        0xf6: "JPG6",
        0xf7: "JPG7",
        0xf8: "JPG8",
        0xf9: "JPG9",
        0xfa: "JPG10",
        0xfb: "JPG11",
        0xfc: "JPG12",
        0xfd: "JPG13",
        0xd0: "RST0",
        0xd1: "RST1",
        0xd2: "RST2",
        0xd3: "RST3",
        0xd4: "RST4",
        0xd5: "RST5",
        0xd6: "RST6",
        0xd7: "RST7",
        0x01: "TEM",
    }

    def identify(buf):
        return buf.peek(3) == b"\xff\xd8\xff"

    def chew(self):
        meta = {}
        meta["type"] = "jpeg"

        meta["chunks"] = []
        while self.buf.available():
            chunk = {}

            assert self.buf.read(1)[0] == 0xff, "wrong marker prefix"
            typ = self.buf.read(1)[0]
            chunk["type"] = self.MARKER_NAME.get(typ, "UNK") + f" (0x{hex(typ)[2:].zfill(2)})"

            if typ in self.HAS_PAYLOAD:
                l = int.from_bytes(self.buf.read(2), "big") - 2
            else:
                l = 0

            self.buf.pushunit()
            self.buf.setunit(l)
            chunk["length"] = l

            chunk["data"] = {}
            if typ == 0xe1 and self.buf.peek(6) == b"Exif\x00\x00":
                chunk["data"]["tiff"] = chew(self.buf.readunit())
            elif typ == 0xe1 and self.buf.peek(4) == b"http":
                ns = b""
                while self.buf.peek(1)[0]:
                    ns += self.buf.read(1)
                self.buf.skip(1)
                chunk["data"]["namespace"] = ns.decode("utf-8")
                chunk["data"]["xmp"] = self.buf.readunit().decode("utf-8")
            elif typ == 0xe2 and self.buf.peek(12) == b"ICC_PROFILE\x00":
                chunk["data"]["icc-profile"] = chew(self.buf.readunit())["data"]
            elif typ == 0xee and self.buf.peek(5) == b"Adobe":
                chunk["data"]["identifier"] = self.buf.read(5).decode("utf-8")
                chunk["data"]["pre-defined"] = self.buf.read(1).hex()
                chunk["data"]["flags0"] = self.buf.read(2).hex()
                chunk["data"]["flags1"] = self.buf.read(2).hex()
                chunk["data"]["transform"] = self.buf.read(1)[0]
            elif typ & 0xf0 == 0xe0:
                chunk["data"]["payload"] = self.buf.readunit().decode("latin-1")
            elif typ == 0xda:
                self.buf.setunit((1<<64) - 1)
                chunk["data"]["image-length"] = self.buf.available() - 2
                self.buf.skip(self.buf.available() - 2)
                self.buf.setunit(0)

            meta["chunks"].append(chunk)

            self.buf.skipunit()
            self.buf.popunit()

        return meta

@module.register
class PngModule(module.RuminaterModule):
    def identify(buf):
        return buf.peek(8) == b"\x89PNG\r\n\x1a\n"

    def chew(self):
        meta = {}
        meta["type"] = "png"

        self.buf.seek(8)
        meta["chunks"] = []
        while self.buf.available():
            length = int.from_bytes(self.buf.read(4), "big")
            self.buf.pushunit()
            self.buf.setunit(length + 8)

            chunk_type = self.buf.read(4)

            chunk = {
                "chunk-type": chunk_type.decode("utf-8"),
                "length": length,
                "flags": {
                    "critical": chunk_type[0] & 32 == 0,
                    "private": chunk_type[1] & 32 == 1,
                    "conforming": chunk_type[2] & 32 == 0,
                    "safe-to-copy": chunk_type[3] & 32 == 1
                },
            }

            data = self.buf.peek(length + 4)
            data, crc = data[:-4], data[-4:]

            chunk["crc"] = {
                "value": crc.hex(),
                "correct": int.from_bytes(crc, "big") == zlib.crc32(chunk_type + data) & 0xffffffff
            }

            chunk["data"] = {}
            match chunk_type:
                case b"IHDR":
                    chunk["data"]["width"] = int.from_bytes(self.buf.read(4), "big")
                    chunk["data"]["height"] = int.from_bytes(self.buf.read(4), "big")
                    chunk["data"]["bit-depth"] = self.buf.read(1)[0]
                    chunk["data"]["color-type"] = self.buf.read(1)[0]
                    chunk["data"]["compression"] = self.buf.read(1)[0]
                    chunk["data"]["filter-method"] = self.buf.read(1)[0]
                    chunk["data"]["interlace-method"] = self.buf.read(1)[0]

            meta["chunks"].append(chunk)

            self.buf.skipunit()
            self.buf.popunit()

        return meta
