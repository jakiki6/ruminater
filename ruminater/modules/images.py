import zlib
from . import chew
from .. import module

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

            print(hex(self.buf.tell()))
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
                chunk["data"]["icc-profile"] = chew(self.buf.readunit())
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
