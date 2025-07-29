from . import chew
from .. import module

import zipfile


@module.register
class ZipModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(4) == b"\x50\x4b\x03\x04"

    def chew(self):
        zf = zipfile.ZipFile(self.buf, "r")

        files = []
        for fileinfo in zf.infolist():
            file = {}
            file["name"] = fileinfo.filename
            file["date"] = fileinfo.date_time
            file["compression-type"] = fileinfo.compress_type
            file["comment"] = fileinfo.comment.decode("utf-8")
            file["extra"] = fileinfo.comment.hex()
            file["create-system"] = fileinfo.create_system
            file["create-version"] = fileinfo.create_version
            file["extract-version"] = fileinfo.extract_version
            file["flag-bits"] = fileinfo.flag_bits
            file["volume"] = fileinfo.volume
            file["internal-attr"] = fileinfo.internal_attr
            file["external-attr"] = fileinfo.external_attr
            file["compress-size"] = fileinfo.compress_size

            file["content"] = chew(zf.open(fileinfo.filename, "r"))

            files.append(file)

        return {
            "type": "zip",
            "comment": zf.comment.decode("utf-8"),
            "files": files,
        }

@module.register
class RIFFModule(module.RuminantModule):
    def identify(buf):
        return buf.peek(4) == b"RIFF"

    def chew(self):
        meta = {}
        meta["type"] = "riff"

        meta["data"] = self.read_chunk()

        return meta

    def read_chunk(self):
        chunk = {}

        typ = self.buf.rs(4)
        if typ == "WEBP":  # why google
            typ = self.buf.rs(4)

        chunk["type"] = typ

        chunk["offset"] = self.buf.tell() - 4

        length = self.buf.ru32l()
        chunk["length"] = length

        self.buf.pushunit()
        self.buf.setunit(((length + 1) >> 1) << 1)

        chunk["data"] = {}
        match typ:
            case "VP8 ":
                tag = self.buf.ru24()
                chunk["data"]["keyframe"] = bool(tag & 0x800000)
                chunk["data"]["version"] = (tag >> 20) & 0x07
                chunk["data"]["show-frame"] = bool(tag & 0x80000)
                chunk["data"]["partition-size"] = tag & 0x7ffff
                chunk["data"]["start-code"] = self.buf.rh(3)
                chunk["data"]["width"] = self.buf.ru16l() & 0x3fff
                chunk["data"]["height"] = self.buf.ru16l() & 0x3fff
            case "VP8L":
                chunk["data"]["signature"] = self.buf.rh(1)
                tag = self.buf.ru32l()
                for field in ("width", "height"):
                    i = 1
                    for j in range(0, 14):
                        i += (tag & 1) << j
                        tag >>= 1

                    chunk["data"][field] = i

                chunk["data"]["has-alpha"] = bool(tag & 1)
                chunk["data"]["version"] = ((tag >> 1) & 1) | (((tag >> 2) & 1) << 1) | (((tag >> 3) & 1) << 2)
            case "ANIM":
                chunk["data"]["background-color"] = {
                    "red": self.buf.ru8(),
                    "green": self.buf.ru8(),
                    "blue": self.buf.ru8(),
                    "alpha": self.buf.ru8()
                }
                chunk["data"]["loop-count"] = self.buf.ru16l()
            case "ANMF":
                chunk["data"]["frame-x"] = self.buf.ru24l()
                chunk["data"]["frame-y"] = self.buf.ru24l()
                chunk["data"]["frame-width"] = self.buf.ru24l() + 1
                chunk["data"]["frame-height"] = self.buf.ru24l() + 1
                chunk["data"]["frame-duration"] = self.buf.ru24l()

                tag = self.buf.ru8()
                chunk["data"]["reserved"] = tag >> 2
                chunk["data"]["alpha-blend"] = not bool(tag & 2)
                chunk["data"]["dispose"] = bool(tag & 1)
            case "ALPH":
                tag = self.buf.ru8()
                chunk["data"]["reserved"] = tag >> 6
                chunk["data"]["preprocessing"] = (tag >> 4) & 0x03
                chunk["data"]["filtering-method"] = (tag >> 2) & 0x03
                chunk["data"]["compression-method"] = tag & 0x03
            case "VP8X":
                tag = self.buf.ru32()
                chunk["data"]["reserved1"] = tag >> 30
                chunk["data"]["has-icc-profile"] = bool(tag & (1 << 29))
                chunk["data"]["has-alpha"] = bool(tag & (1 << 28))
                chunk["data"]["has-exif"] = bool(tag & (1 << 27))
                chunk["data"]["has-xmp"] = bool(tag & (1 << 26))
                chunk["data"]["has-animation"] = bool(tag & (1 << 25))
                chunk["data"]["reserved2"] = tag & 0x1ffffff
                chunk["data"]["width"] = self.buf.ru24l() + 1
                chunk["data"]["height"] = self.buf.ru24l() + 1
            case "RIFF" | "LIST":
                chunk["data"]["chunks"] = []
                while self.buf.unit:
                    chunk["data"]["chunks"].append(self.read_chunk())
            case _:
                chunk["data"]["unknown"] = True

        self.buf.skipunit()
        self.buf.popunit()

        return chunk
