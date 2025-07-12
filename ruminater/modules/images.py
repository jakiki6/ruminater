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

    class PngModule(module.RuminaterModule):
        def chew(self):
            img = Image.open(self.buf)

            meta = {}
            meta["type"] = "png"
            meta["width"], meta["height"] = img.size
            meta["mode"] = img.mode

            self.buf.seek(8)
            meta["chunks"] = []
            try:
                while True:
                    length = int.from_bytes(self.buf.read(4), "big")
                    chunk_type = self.buf.read(4)
                    self.buf.read(length + 4)

                    meta["chunks"].append({"chunk-type": chunk_type.decode("utf-8"), "length": length, "critical": chunk_type[0] & 32 == 0, "private": chunk_type[1] & 32 == 1, "conforming": chunk_type[2] & 32 == 0, "safe-to-copy": chunk_type[3] & 32 == 1})

                    if chunk_type == b"IEND" and False:
                        break
            except:
                pass

            return meta

    mappings["^PNG.*$"] = PngModule
except ModuleNotFoundError:
    print("pillow not found, skipping JPEG and PNG parsing")
