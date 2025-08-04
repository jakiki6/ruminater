from .. import module
from . import chew


@module.register
class FlacModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(4) == b"fLaC"

    def chew(self):
        meta = {}
        meta["type"] = "flac"

        self.buf.skip(4)

        meta["blocks"] = []
        more = True
        while more:
            block = {}
            block["type"] = None

            flags = self.buf.ru8()
            more = not bool(flags & 0x80)
            typ = flags & 0x7f

            length = self.buf.ru24()
            block["length"] = length

            self.buf.pushunit()
            self.buf.setunit(length)

            block["data"] = {}
            match typ:
                case 0:
                    block["type"] = "Streaminfo"
                    block["data"]["min-block-size"] = self.buf.ru16()
                    block["data"]["max-block-size"] = self.buf.ru16()
                    block["data"]["min-frame-size"] = self.buf.ru24()
                    block["data"]["max-frame-size"] = self.buf.ru24()

                    temp = self.buf.ru64()
                    block["data"]["sample-rate"] = temp >> 44
                    block["data"]["channel-count"] = ((temp >> 41) & 0x07) + 1
                    block["data"]["bits-per-sample"] = (
                        (temp >> 36) & 0x1f) + 1
                    block["data"]["sample-count"] = temp & 0xfffffffff

                    block["data"]["unencoded-md5"] = self.buf.rh(16)
                case 1:
                    block["type"] = "Padding"
                    block["data"]["non-zero"] = sum(self.buf.readunit()) > 0
                case 2:
                    block["type"] = "Application"
                    block["data"]["application-id"] = self.buf.rs(4, "latin-1")
                case 4:
                    block["type"] = "Vorbis comment"
                    block["data"]["vendor-string"] = self.buf.rs(
                        self.buf.ru32l())

                    block["data"]["user-strings"] = []
                    for i in range(0, self.buf.ru32l()):
                        block["data"]["user-strings"].append(
                            self.buf.rs(self.buf.ru32l()))
                case 6:
                    block["type"] = "Picture"
                    picture_type = self.buf.ru32()
                    block["data"]["picture-type"] = {
                        0: "Other",
                        1: "PNG file icon of 32x32 pixels (see [RFC2083])",
                        2: "General file icon",
                        3: "Front cover",
                        4: "Back cover",
                        5: "Liner notes page",
                        6: "Media label (e.g., CD, Vinyl or Cassette label)",
                        7: "Lead artist, lead performer, or soloist",
                        8: "Artist or performer",
                        9: "Conductor",
                        10: "Band or orchestra",
                        11: "Composer",
                        12: "Lyricist or text writer",
                        13: "Recording location",
                        14: "During recording",
                        15: "During performance",
                        16: "Movie or video screen capture",
                        17: "A bright colored fish",
                        18: "Illustration",
                        19: "Band or artist logotype",
                        20: "Publisher or studio logotype"
                    }.get(picture_type,
                          "Unknown") + f" (0x{hex(picture_type)[2:].zfill(4)})"
                    block["data"]["media-type"] = self.buf.rs(self.buf.ru32())
                    block["data"]["description"] = self.buf.rs(self.buf.ru32())
                    block["data"]["width"] = self.buf.ru32()
                    block["data"]["height"] = self.buf.ru32()
                    block["data"]["bits-per-pixel"] = self.buf.ru32()
                    block["data"]["palette-element-count"] = self.buf.ru32()
                    block["data"]["picture"] = chew(
                        self.buf.read(self.buf.ru32()))
                case _:
                    block["type"] = f"Unknown (0x{hex(typ)[2:].zfill(2)})"
                    block["unknown"] = True

            meta["blocks"].append(block)

            self.buf.skipunit()
            self.buf.popunit()

        return meta
