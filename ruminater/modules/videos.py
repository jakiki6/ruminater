import uuid
from . import mappings, chew
from .. import module

class Mp4Module(module.RuminaterModule):
    def chew(self):
        file = {}

        file["type"] = "mp4"
        file["atoms"] = []
        while not self.blob.isend():
            file["atoms"].append(self.read_atom())

        return file

    def read_atom(self):
        offset = self.blob.tell()

        length = int.from_bytes(self.blob.read(4), "big")
        if length == 0:
            pos = self.blob.tell()
            self.blob.seek(0, 2)
            length = self.blob.tell()
            self.blob.seek(pos)
        typ = self.blob.read(4).decode("utf-8")

        if length == 1:
            length = int.from_bytes(self.blob.read(8), "big")

        atom = {
            "type": typ,
            "offset": offset,
            "length" : length,
            "data": {}
        }

        length -= 8

        if typ == "ftyp":
            atom["data"]["major_brand"] = self.blob.read(4).decode()
            atom["data"]["minor_version"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["compatible_brands"] = []

            length -= 8
            while length > 0:
                atom["data"]["compatible_brands"].append(self.blob.read(4).decode())
                length -= 4
        elif typ == "moov":
            atom["data"]["atoms"] = []
            while length > 0:
                data = self.read_atom()
                atom["data"]["atoms"].append(data)
                length -= data["length"]
        elif typ == "uuid":
            atom["data"]["uuid"] = str(uuid.UUID(bytes=self.blob.read(16)))
            length -= 16

            if length > 0:
                atom["data"]["user-data"] = self.blob.read(length).decode("utf-8")
        else:
            self.blob.skip(length)

        return atom

mappings["^ISO Media.*$"] = Mp4Module
