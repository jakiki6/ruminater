from . import chew
from .. import module

import zipfile

@module.register
class ZipModule(module.RuminaterModule):
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

        return {"type": "zip", "comment": zf.comment.decode("utf-8"), "files": files}
