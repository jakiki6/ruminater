from . import chew
from .. import module, utils

import tempfile


@module.register
class ZipModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(4) == b"\x50\x4b\x03\x04"

    def chew(self):
        meta = {}
        meta["type"] = "zip"

        self.buf.search(b"\x50\x4b\x05\x06")

        self.buf.skip(4)
        meta["eocd"] = {}
        meta["eocd"]["disc-count"] = self.buf.ru16l()
        meta["eocd"]["central-directory-first-disk"] = self.buf.ru16l()
        meta["eocd"]["central-directory-local-count"] = self.buf.ru16l()
        meta["eocd"]["central-directory-global-count"] = self.buf.ru16l()
        meta["eocd"]["central-directory-size"] = self.buf.ru32l()
        meta["eocd"]["central-directory-offset"] = self.buf.ru32l()
        meta["eocd"]["comment"] = self.buf.rs(self.buf.ru16l())
        eof = self.buf.tell()

        self.buf.seek(meta["eocd"]["central-directory-offset"])

        meta["files"] = []
        while self.buf.pu32() == 0x504b0102:
            self.buf.skip(4)

            file = {}
            file["meta"] = {}
            file["meta"]["version-producer"] = self.buf.ru16l()
            file["meta"]["version-needed"] = self.buf.ru16l()
            file["meta"]["general-flags"] = self.buf.rh(2)
            file["meta"]["compression-method"] = self.buf.ru16l()
            file["meta"]["modification-time"] = self.buf.ru16l()
            file["meta"]["modification-date"] = self.buf.ru16l()
            file["meta"]["crc32"] = self.buf.rh(4)
            file["meta"]["compressed-size"] = self.buf.ru32l()
            file["uncompressed-size"] = self.buf.ru32l()
            filename_length = self.buf.ru16l()
            extra_field_length = self.buf.ru16l()
            comment_length = self.buf.ru16l()
            file["meta"]["start-disk"] = self.buf.ru16l()
            file["meta"]["internal-attributes"] = self.buf.rh(2)
            file["meta"]["external-attributes"] = self.buf.rh(4)
            file["offset"] = self.buf.ru32l()
            file["filename"] = self.buf.rs(filename_length)
            file["meta"]["extra-field"] = self.buf.rs(extra_field_length)
            file["meta"]["comment"] = self.buf.rs(comment_length)

            with self.buf:
                self.buf.seek(file["offset"])
                assert self.buf.ru32() == 0x504b0304, "broken ZIP file"
                self.buf.skip(22)
                self.buf.skip(self.buf.ru16l() + self.buf.ru16l())

                match file["meta"]["compression-method"]:
                    case 0:
                        with self.buf.sub(file["uncompressed-size"]):
                            file["data"] = chew(self.buf)

                    case 8:
                        with self.buf.sub(file["meta"]["compressed-size"]):
                            fd = tempfile.TemporaryFile()
                            utils.stream_deflate(self.buf, fd,
                                                 self.buf.available())
                            fd.seek(0)

                            file["data"] = chew(fd)

            meta["files"].append(file)

        self.buf.seek(eof)
        return meta


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
                chunk["data"]["version"] = ((tag >> 1) & 1) | ((
                    (tag >> 2) & 1) << 1) | (((tag >> 3) & 1) << 2)
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
            case "fmt ":
                chunk["data"]["format"] = self.buf.ru16l()
                chunk["data"]["channel-count"] = self.buf.ru16l()
                chunk["data"]["sample-rate"] = self.buf.ru32l()
                chunk["data"]["byte-rate"] = self.buf.ru32l()
                chunk["data"]["block-align"] = self.buf.ru16l()
                chunk["data"]["bits-per-sample"] = self.buf.ru16l()
            case "RIFF":
                chunk["data"]["filetype"] = self.buf.rs(4)
                chunk["data"]["chunks"] = []
                while self.buf.unit:
                    chunk["data"]["chunks"].append(self.read_chunk())
            case "LIST":
                chunk["data"]["chunks"] = []
                while self.buf.unit:
                    chunk["data"]["chunks"].append(self.read_chunk())
            case "data":
                pass
            case _:
                chunk["data"]["unknown"] = True

        self.buf.skipunit()
        self.buf.popunit()

        return chunk
