import uuid
from datetime import datetime, timezone, timedelta
from . import mappings, chew
from .. import module


def mp4_time_to_iso(mp4_time):
    mp4_epoch = datetime(1904, 1, 1, tzinfo=timezone.utc)
    dt = mp4_epoch + timedelta(seconds=mp4_time)
    return dt.isoformat()

def mp4_decode_mdhd_language(lang_bytes):
    lang_code = int.from_bytes(lang_bytes, byteorder="big") & 0x7fff

    c1 = ((lang_code >> 10) & 0x1F) + 0x60
    c2 = ((lang_code >> 5)  & 0x1F) + 0x60
    c3 = ( lang_code        & 0x1F) + 0x60

    return chr(c1) + chr(c2) + chr(c3)

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
        typ = self.blob.read(4).decode("latin-1")

        if length == 1:
            length = int.from_bytes(self.blob.read(8), "big")

        atom = {
            "type": typ,
            "offset": offset,
            "length" : length,
            "data": {}
        }

        length -= 8
        self.blob.pushunit()
        self.blob.set_unit(length)

        if typ in ("moov", "trak", "mdia", "minf", "dinf", "stbl", "udta", "ilst", "mvex", "moof") or (typ[0] == "©" and self.blob.peek(8)[4:8] == b"data"):
            atom["data"]["atoms"] = []
            while self.blob.unit > 0:
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "ftyp":
            atom["data"]["major_brand"] = self.blob.read(4).decode("utf-8")
            atom["data"]["minor_version"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["compatible_brands"] = []

            while self.blob.unit > 0:
                atom["data"]["compatible_brands"].append(self.blob.read(4).decode("utf-8"))
        elif typ == "uuid":
            atom["data"]["uuid"] = str(uuid.UUID(bytes=self.blob.read(16)))

            if self.blob.unit > 0:
                atom["data"]["user-data"] = self.blob.read(length).decode("utf-8")
        elif typ == "mvhd":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            if version == 0:
                creation_time = int.from_bytes(self.blob.read(4), "big")
                modification_time = int.from_bytes(self.blob.read(4), "big")
                timescale = int.from_bytes(self.blob.read(4), "big")
                duration = int.from_bytes(self.blob.read(4), "big")
            elif version == 1:
                creation_time = int.from_bytes(self.blob.read(8), "big")
                modification_time = int.from_bytes(self.blob.read(8), "big")
                timescale = int.from_bytes(self.blob.read(4), "big")
                duration = int.from_bytes(self.blob.read(8), "big")

            if version in (0, 1):
                atom["data"]["creation_time"] = mp4_time_to_iso(creation_time)
                atom["data"]["modification_time"] = mp4_time_to_iso(modification_time)
                atom["data"]["timescale"] = timescale
                atom["data"]["duration"] = duration

                atom["data"]["rate"] = int.from_bytes(self.blob.read(4), "big") / 65536
                atom["data"]["volume"] = int.from_bytes(self.blob.read(2), "big") / 256
                atom["data"]["reserved"] = self.blob.read(10).hex()
                atom["data"]["matrix"] = self.blob.read(36).hex()
                atom["data"]["pre_defined"] = self.blob.read(24).hex()
                atom["data"]["next_track_ID"] = int.from_bytes(self.blob.read(4), "big")
        elif typ == "tkhd":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "enabled": bool(flags & 1),
                "movie": bool(flags & 2),
                "preview": bool(flags & 4)
            }

            if version == 0:
                creation_time = int.from_bytes(self.blob.read(4), "big")
                modification_time = int.from_bytes(self.blob.read(4), "big")
                track_ID = int.from_bytes(self.blob.read(4), "big")
                reserved1 = self.blob.read(4)
                duration = int.from_bytes(self.blob.read(4), "big")

            if version == 1:
                creation_time = int.from_bytes(self.blob.read(8), "big")
                modification_time = int.from_bytes(self.blob.read(8), "big")
                track_ID = int.from_bytes(self.blob.read(4), "big")
                reserved1 = self.blob.read(4)
                duration = int.from_bytes(self.blob.read(8), "big")

            if version in (0, 1):
                atom["data"]["creation_time"] = mp4_time_to_iso(creation_time)
                atom["data"]["modification_time"] = mp4_time_to_iso(modification_time)
                atom["data"]["track_ID"] = track_ID
                atom["data"]["reserved1"] = reserved1.hex()
                atom["data"]["duration"] = duration

                atom["data"]["reserved2"] = self.blob.read(8).hex()
                atom["data"]["layer"] = int.from_bytes(self.blob.read(2), "big")
                atom["data"]["alternate_group"] = int.from_bytes(self.blob.read(2), "big")
                atom["data"]["volume"] = int.from_bytes(self.blob.read(2), "big") / 256
                atom["data"]["reserved3"] = self.blob.read(2).hex()
                atom["data"]["matrix"] = self.blob.read(36).hex()
                atom["data"]["width"] = int.from_bytes(self.blob.read(4), "big") / 65536
                atom["data"]["height"] = int.from_bytes(self.blob.read(4), "big") / 65536
        elif typ == "edts":
            atom["data"] = self.read_atom()
        elif typ == "elst":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["entries"] = []
            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count

            for i in range(0, entry_count):
                if version == 0:
                    segment_duration = int.from_bytes(self.blob.read(4), "big")
                    media_time = int.from_bytes(self.blob.read(4), "big")
                elif version == 1:
                    segment_duration = int.from_bytes(self.blob.read(8), "big")
                    media_time = int.from_bytes(self.blob.read(8), "big")

                if version in (0, 1):
                    entry = {}
                    entry["segment_duration"] = segment_duration
                    entry["media_time"] = media_time
                    entry["media_rate_integer"] = int.from_bytes(self.blob.read(2), "big")
                    entry["media_rate_fraction"] = int.from_bytes(self.blob.read(2), "big")

                    atom["data"]["entries"].append(entry)
        elif typ == "mdhd":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            if version == 0:
                creation_time = int.from_bytes(self.blob.read(4), "big")
                modification_time = int.from_bytes(self.blob.read(4), "big")
                timescale = int.from_bytes(self.blob.read(4), "big")
                duration = int.from_bytes(self.blob.read(4), "big")
            elif version == 1:
                creation_time = int.from_bytes(self.blob.read(8), "big")
                modification_time = int.from_bytes(self.blob.read(8), "big")
                timescale = int.from_bytes(self.blob.read(4), "big")
                duration = int.from_bytes(self.blob.read(8), "big")

            if version in (0, 1):
                atom["data"]["creation_time"] = mp4_time_to_iso(creation_time)
                atom["data"]["modification_time"] = mp4_time_to_iso(modification_time)
                atom["data"]["timescale"] = timescale
                atom["data"]["duration"] = duration

                atom["data"]["language"] = mp4_decode_mdhd_language(self.blob.read(2))
                atom["data"]["pre_defined"] = self.blob.read(2).hex()
        elif typ == "hdlr":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["pre_defined"] = self.blob.read(4).hex()
            atom["data"]["handler_type"] = self.blob.read(4).decode("utf-8")
            atom["data"]["reserved"] = self.blob.read(12).hex()
            atom["data"]["name"] = self.blob.readunit()[:-1].decode("utf-8")
        elif typ == "vmhd":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["graphicsmode"] = int.from_bytes(self.blob.read(2), "big") 
            atom["data"]["opcolor"] = [int.from_bytes(self.blob.read(2), "big") for _ in range(0, 3)]
        elif typ in ("dref", "stsd"):
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            entry_count = int.from_bytes(self.blob.read(4), "big")

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                atom["data"]["entries"].append(self.read_atom())
        elif typ == "url ":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "local": bool(flags & 1)
            }

            atom["data"]["location"] = self.blob.readunit()[:-1].decode("utf-8")
        elif typ == "avc1":
            atom["data"]["reserved1"] = self.blob.read(6).hex()
            atom["data"]["data_reference_index"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["pre_defined1"] = self.blob.read(2).hex()
            atom["data"]["reserved2"] = self.blob.read(2).hex()
            atom["data"]["pre_defined2"] = self.blob.read(12).hex()
            atom["data"]["width"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["height"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["horizresolution"] = int.from_bytes(self.blob.read(4), "big") / 65536
            atom["data"]["vertresolution"] = int.from_bytes(self.blob.read(4), "big") / 65536
            atom["data"]["reserved3"] = self.blob.read(4).hex()
            atom["data"]["frame_count"] = int.from_bytes(self.blob.read(2), "big")
            l = self.blob.read(1)[0]
            name = self.blob.read(31)
            atom["data"]["compressorname"] = name[:l].decode("utf-8")
            atom["data"]["depth"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["pre_defined3"] = self.blob.read(2).hex()

            atom["data"]["atoms"] = []
            while self.blob.unit > 0:
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "avcC":
            atom["data"]["configurationVersion"] = self.blob.read(1)[0]
            atom["data"]["AVCProfileIndication"] = self.blob.read(1)[0]
            atom["data"]["profile_compatibility"] = self.blob.read(1)[0]
            atom["data"]["AVCLevelIndication"] = self.blob.read(1)[0]
            atom["data"]["lengthSizeMinusOne"] = self.blob.read(1)[0]

            atom["data"]["numOfSequenceParameterSets"] = self.blob.read(1)[0]
            atom["data"]["sequenceParameterSets"] = []
            for i in range(0, atom["data"]["numOfSequenceParameterSets"] & 0b00011111):
                l = int.from_bytes(self.blob.read(2), "big")
                atom["data"]["sequenceParameterSets"].append(self.blob.read(l).hex())

            atom["data"]["numOfPictureParameterSets"] = self.blob.read(1)[0]
            atom["data"]["pictureParameterSets"] = []
            for i in range(0, atom["data"]["numOfPictureParameterSets"]):
                l = int.from_bytes(self.blob.read(2), "big")
                atom["data"]["pictureParameterSets"].append(self.blob.read(l).hex())
        elif typ == "colr":
            atom["data"]["color_type"] = self.blob.read(4).decode("utf-8")

            match atom["data"]["color_type"]:
                case "nclc":
                    atom["data"]["color_primaries"] = int.from_bytes(self.blob.read(2), "big")
                    atom["data"]["transfer_characteristics"] = int.from_bytes(self.blob.read(2), "big")
                    atom["data"]["matrix_coefficients"] = int.from_bytes(self.blob.read(2), "big")
                case "rICC" | "prof":
                    atom["data"]["icc_profile_data"] = self.blob.readunit().hex()
                case "nclx":
                    atom["data"]["color_primaries"] = int.from_bytes(self.blob.read(2), "big")
                    atom["data"]["transfer_characteristics"] = int.from_bytes(self.blob.read(2), "big")
                    atom["data"]["matrix_coefficients"] = int.from_bytes(self.blob.read(2), "big")
                    full_range_flag = self.blob.read(1)[0]
                    atom["data"]["full_range_flag"] = {
                        "raw": full_range_flag,
                        "full": bool(full_range_flag & 0x80)
                    }
        elif typ == "pasp":
            atom["data"]["hSpacing"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["vSpacing"] = int.from_bytes(self.blob.read(4), "big")
        elif typ == "btrt":
            atom["data"]["buffer_size"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["max_bitrate"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["avg_bitrate"] = int.from_bytes(self.blob.read(4), "big")
        elif typ == "stts":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "stss":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "ctts":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "stsc":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "stsz":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["sample_size"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["sample_count"] = int.from_bytes(self.blob.read(4), "big")
        elif typ == "stco":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "sgpd":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "variable_length": bool(flags & 1)
            }

            atom["data"]["grouping_type"] = self.blob.read(4).decode("utf-8")

            default_length = 0
            if version == 1 and flags & 1 == 0:
                default_length = int.from_bytes(self.blob.read(4), "big")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                length = default_length
                if length == 0:
                    length = int.from_bytes(self.blob.read(4), "big")

                atom["data"]["entries"].append(self.blob.read(length).hex())
        elif typ == "sbgp":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            atom["data"]["grouping_type"] = self.blob.read(4).decode("utf-8")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                atom["data"]["entries"].append({
                    "sample_count": int.from_bytes(self.blob.read(4), "big"),
                    "group_description_index": int.from_bytes(self.blob.read(4), "big")
                })
        elif typ == "smhd":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["balance"] = int.from_bytes(self.blob.read(2), "big") / 256
            atom["data"]["reserved"] = int.from_bytes(self.blob.read(2), "big")
        elif typ == "mp4a":
            atom["data"]["reserved1"] = self.blob.read(6).hex()
            atom["data"]["data_reference_index"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["reserved2"] = self.blob.read(8).hex()
            atom["data"]["channel_count"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["samplesize"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["pre_defined"] = self.blob.read(2).hex()
            atom["data"]["reserved3"] = self.blob.read(2).hex()
            atom["data"]["samplerate"] = int.from_bytes(self.blob.read(4), "big") / 65536

            atom["data"]["atoms"] = []
            while self.blob.unit > 0:
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "esds":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            atom["data"]["ES_descriptor"] = self.blob.readunit().hex()
        elif typ == "meta":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            atom["data"]["atoms"] = []
            while self.blob.unit > 0:
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "data":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["type"] = int.from_bytes(self.blob.read(4), "big")

            match atom["data"]["type"]:
                case 0:
                    atom["data"]["payload"] = self.blob.readunit().decode("utf-8")
                case 1:
                    atom["data"]["payload"] = self.blob.readunit().decode("utf-16")
                case _:
                    atom["data"]["payload"] = self.blob.readunit().hex()
        elif typ == "free":
            atom["data"]["non-zero"] = sum(self.blob.readunit()) > 0
        elif typ == "mdat":
            self.blob.skipunit()
        elif typ == "co64":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")

            entry_count = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "sdtp":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["sample_dep_type_count"] = len(self.blob.readunit())
        elif typ[0] == "©":
            atom["data"]["payload"] = self.blob.readunit().hex()
        elif typ == "vp09":
            atom["data"]["reserved1"] = self.blob.read(6).hex()
            atom["data"]["data_reference_index"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["pre_defined1"] = self.blob.read(2).hex()
            atom["data"]["reserved2"] = self.blob.read(2).hex()
            atom["data"]["pre_defined2"] = self.blob.read(12).hex()
            atom["data"]["width"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["height"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["horizresolution"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["vertresolution"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["reserved3"] = self.blob.read(4).hex()
            atom["data"]["frame_count"] = int.from_bytes(self.blob.read(2), "big")
            l = self.blob.read(1)[0]
            name = self.blob.read(31)
            atom["data"]["compressorname"] = name[:l].decode("utf-8")
            atom["data"]["depth"] = int.from_bytes(self.blob.read(2), "big")
            atom["data"]["pre_defined3"] = self.blob.read(2).hex()

            atom["data"]["atoms"] = []
            while self.blob.unit > 0:
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "vpcC":
            atom["data"]["profile"] = self.blob.read(1)[0]
            atom["data"]["level"] = self.blob.read(1)[0]
            atom["data"]["bit_depth"] = self.blob.read(1)[0]
            atom["data"]["chroma_subsampling"] = self.blob.read(1)[0]
            atom["data"]["video_full_range_flag"] = self.blob.read(1)[0]
            atom["data"]["reserved"] = self.blob.read(3).hex()
        elif typ == "trex":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["track_ID"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["default_sample_description_index"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["default_sample_duration"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["default_sample_size"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["default_sample_flags"] = int.from_bytes(self.blob.read(4), "big")
        elif typ == "sidx":
            version = self.blob.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["flags"] = int.from_bytes(self.blob.read(3), "big")
            atom["data"]["reference_ID"] = int.from_bytes(self.blob.read(4), "big")
            atom["data"]["earliest_presentation_time"] = int.from_bytes(self.blob.read(4 if version == 0 else 8), "big")
            atom["data"]["first_offset"] = int.from_bytes(self.blob.read(4 if version == 0 else 8), "big")
            atom["data"]["reserved"] = self.blob.read(2).hex()
            atom["data"]["reference_count"] = int.from_bytes(self.blob.read(2), "big")
        else:
            atom["unknown"] = True

        self.blob.skipunit()
        self.blob.popunit()

        return atom

mappings["^ISO Media.*$"] = Mp4Module
