from . import mappings, chew
from .. import module

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
except ModuleNotFoundError:
    print("pymp4 not installed, skipping MP4 parsing")
