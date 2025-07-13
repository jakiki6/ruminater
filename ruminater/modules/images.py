import zlib
from . import mappings, chew
from .. import module

try:
    from PIL import Image, ExifTags

    class JpegModule(module.RuminaterModule):
        @staticmethod
        def _sanitize(val):
            if str(type(val)) == "<class 'PIL.TiffImagePlugin.IFDRational'>":
                return float(val)
            elif type(val) == tuple or type(val) == tuple:
                res = [JpegModule._sanitize(x) for x in val]

                if type(val) == tuple:
                    res = tuple(res)

                return res
            elif type(val) == bytes or type(val) == bytearray:
                return val.hex()

            try:
                json.dumps(val)
                return val
            except:
                return str(val)

        def chew(self):
            img = Image.open(self.buf)

            meta = {}
            meta["type"] = "jpeg"
            meta["width"], meta["height"] = img.size
            meta["mode"] = img.mode

            meta["exif"] = {}

            for key, val in img.getexif().items():
                val = self._sanitize(val)

                if key in ExifTags.TAGS:
                    meta["exif"][ExifTags.TAGS[key]] = val
                else:
                    meta["exif"][f"unknown_{key}"] = val

            for ifd_id in ExifTags.IFD:
                try:
                    ifd = img.getexif().get_ifd(ifd_id)

                    if ifd_id == ExifTags.IFD.GPSInfo:
                        resolve = ExifTags.GPSTAGS
                    else:
                        resolve = ExifTags.TAGS

                    for key, val in ifd.items():
                        val = self._sanitize(val)

                        meta["exif"][resolve[key]] = val
                except KeyError:
                    pass

            return meta

    mappings["^JPEG.*$"] = JpegModule
except ModuleNotFoundError:
    print("pillow not found, skipping JPEG parsing")

class PngModule(module.RuminaterModule):
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

mappings["^PNG.*$"] = PngModule
