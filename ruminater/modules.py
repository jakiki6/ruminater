import magic, json, hashlib
from . import module

mappings = {}

class EntryModule(module.RuminaterModule):
    def chew(self):
        data = self.blob.read()
        self.blob.seek(0)

        meta = {}

        data_type = magic.from_buffer(data)
        data_len = len(data)
        data_hash = hashlib.sha256(data).hexdigest()

        meta["length"] = data_len
        meta["hash-sha256"] = data_hash

        del data    # free RAM

        if data_type.split(",")[0] in mappings:
            meta |= mappings[data_type.split(",")[0]](self.blob).chew()
        else:
            meta |= {"type": "blob", "libmagic-type": data_type}

        return meta

def chew(blob):
    return EntryModule(blob).chew()

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
            img = Image.open(self.blob)

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

    mappings["JPEG image data"] = JpegModule
except:
    print("pillow not found, skipping JPEG parsing")

import zipfile

class ZipModule(module.RuminaterModule):
    def chew(self):
        zf = zipfile.ZipFile(self.blob, "r")

        files = []
        for fileinfo in zf.infolist():
            print(fileinfo, dir(fileinfo))

            file = {}
            file["name"] = fileinfo.filename
            file["content"] = chew(zf.open(fileinfo.filename, "r"))

            files.append(file)

        return {"files": files}

mappings["Zip archive data"] = ZipModule
