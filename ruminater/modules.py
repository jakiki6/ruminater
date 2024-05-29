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

        return {"type": "zip", "comment": zf.comment.decode("utf-8"), "files": files}

mappings["Zip archive data"] = ZipModule

try:
    from pymp4.parser import Box

    class Mp4Module(module.RuminaterModule):
        def chew(self):
            ftyp = dict(Box.parse(self.blob.read()))
            file = {}
            file["type"] = "mp4"
            file["mp4-type"] = ftyp["type"].decode("utf-8")
            file["major-brand"] = ftyp["major_brand"].decode("utf-8")
            file["minor-version"] = ftyp["minor_version"]
            file["compatible-brands"] = [x.decode("utf-8") for x in ftyp["compatible_brands"]]

            return file

    mappings["ISO Media"] = Mp4Module
except:
    print("pymp4 not installed, skipping MP4 parsing")
