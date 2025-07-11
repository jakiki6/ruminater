import uuid
from datetime import datetime, timezone, timedelta
from . import mappings, chew
from .. import module


def mp4_time_to_iso(mp4_time):
    mp4_epoch = datetime(1904, 1, 1, tzinfo=timezone.utc)
    dt = mp4_epoch + timedelta(seconds=mp4_time)
    return dt.isoformat()


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
        elif typ == "mvhd":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            length -= 4

            if version == 0:
                creation_time = int.from_bytes(self.blob.read(4), "big")
                modification_time = int.from_bytes(self.blob.read(4), "big")
                timescale = int.from_bytes(self.blob.read(4), "big")
                duration = int.from_bytes(self.blob.read(4), "big")
                length -= 16
            elif version == 1:
                creation_time = int.from_bytes(self.blob.read(8), "big")
                modification_time = int.from_bytes(self.blob.read(8), "big")
                timescale = int.from_bytes(self.blob.read(4), "big")
                duration = int.from_bytes(self.blob.read(8), "big")
                length -= 28

            if version in (0, 1):
                atom["data"]["creation_time"] = mp4_time_to_iso(creation_time)
                atom["data"]["modification_time"] = mp4_time_to_iso(modification_time)

                atom["data"]["rate"] = int.from_bytes(self.blob.read(4), "big") / 65536
                atom["data"]["volume"] = int.from_bytes(self.blob.read(2), "big") / 256
                atom["data"]["reserved"] = self.blob.read(10).hex()
                atom["data"]["matrix"] = self.blob.read(36).hex()
                atom["data"]["pre_defined"] = self.blob.read(24).hex()
                atom["data"]["next_track_ID"] = int.from_bytes(self.blob.read(4), "big")

                length -= 80

            self.blob.skip(length)
        else:
            self.blob.skip(length)

        return atom

mappings["^ISO Media.*$"] = Mp4Module
