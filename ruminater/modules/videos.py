import uuid
from datetime import datetime, timezone, timedelta
from . import chew
from .. import module, utils

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

@module.register
class Mp4Module(module.RuminaterModule):
    def identify(buf):
        return buf.peek(8)[4:] == b"ftyp"

    def chew(self):
        file = {}

        file["type"] = "mp4"
        file["atoms"] = []
        while not self.buf.isend():
            file["atoms"].append(self.read_atom())

        self.parse_mdat(file["atoms"])

        return file

    def read_version(self, atom):
        version = self.buf.read(1)[0]
        atom["data"]["version"] = version
        atom["data"]["flags"] = int.from_bytes(self.buf.read(3), "big")
        return version

    def read_more(self, atom):
        atom["data"]["atoms"] = []

        bak = self.buf.backup()

        while self.buf.unit > 0:
            try:
                atom["data"]["atoms"].append(self.read_atom())
            except:
                break

        self.buf.restore(bak)
        self.buf.skipunit()

    def read_atom(self):
        offset = self.buf.tell()

        length = int.from_bytes(self.buf.read(4), "big")
        if length == 0:
            pos = self.buf.tell()
            self.buf.seek(0, 2)
            length = self.buf.tell()
            self.buf.seek(pos)
        typ = self.buf.read(4).decode("latin-1")

        if length == 1:
            length = int.from_bytes(self.buf.read(8), "big")

        atom = {
            "type": typ,
            "offset": offset,
            "length" : length,
            "data": {}
        }

        length -= 8
        self.buf.pushunit()
        self.buf.setunit(length)

        if typ in ("moov", "trak", "mdia", "minf", "dinf", "stbl", "udta", "ilst", "mvex", "moof", "traf", "gsst", "gstd") or (typ[0] == "©" and self.buf.peek(8)[4:8] == b"data"):
            self.read_more(atom)
        elif typ == "ftyp":
            atom["data"]["major_brand"] = self.buf.read(4).decode("utf-8")
            atom["data"]["minor_version"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["compatible_brands"] = []

            while self.buf.unit > 0:
                atom["data"]["compatible_brands"].append(self.buf.read(4).decode("utf-8"))
        elif typ == "uuid":
            atom["data"]["uuid"] = str(uuid.UUID(bytes=self.buf.read(16)))
            atom["data"]["user-data"] = self.buf.readunit().decode("utf-8")
            try:
                atom["data"]["user-data"] = utils.xml_to_dict(atom["data"]["user-data"])
            except:
                pass
        elif typ == "mvhd":
            version = self.read_version(atom)

            if version == 0:
                creation_time = int.from_bytes(self.buf.read(4), "big")
                modification_time = int.from_bytes(self.buf.read(4), "big")
                timescale = int.from_bytes(self.buf.read(4), "big")
                duration = int.from_bytes(self.buf.read(4), "big")
            elif version == 1:
                creation_time = int.from_bytes(self.buf.read(8), "big")
                modification_time = int.from_bytes(self.buf.read(8), "big")
                timescale = int.from_bytes(self.buf.read(4), "big")
                duration = int.from_bytes(self.buf.read(8), "big")

            if version in (0, 1):
                atom["data"]["creation_time"] = mp4_time_to_iso(creation_time)
                atom["data"]["modification_time"] = mp4_time_to_iso(modification_time)
                atom["data"]["timescale"] = timescale
                atom["data"]["duration"] = duration

                atom["data"]["rate"] = int.from_bytes(self.buf.read(4), "big") / 65536
                atom["data"]["volume"] = int.from_bytes(self.buf.read(2), "big") / 256
                atom["data"]["reserved"] = self.buf.read(10).hex()
                atom["data"]["matrix"] = self.buf.read(36).hex()
                atom["data"]["pre_defined"] = self.buf.read(24).hex()
                atom["data"]["next_track_ID"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "tkhd":
            version = self.buf.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.buf.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "enabled": bool(flags & 1),
                "movie": bool(flags & 2),
                "preview": bool(flags & 4)
            }

            if version == 0:
                creation_time = int.from_bytes(self.buf.read(4), "big")
                modification_time = int.from_bytes(self.buf.read(4), "big")
                track_ID = int.from_bytes(self.buf.read(4), "big")
                reserved1 = self.buf.read(4)
                duration = int.from_bytes(self.buf.read(4), "big")

            if version == 1:
                creation_time = int.from_bytes(self.buf.read(8), "big")
                modification_time = int.from_bytes(self.buf.read(8), "big")
                track_ID = int.from_bytes(self.buf.read(4), "big")
                reserved1 = self.buf.read(4)
                duration = int.from_bytes(self.buf.read(8), "big")

            if version in (0, 1):
                atom["data"]["creation_time"] = mp4_time_to_iso(creation_time)
                atom["data"]["modification_time"] = mp4_time_to_iso(modification_time)
                atom["data"]["track_ID"] = track_ID
                atom["data"]["reserved1"] = reserved1.hex()
                atom["data"]["duration"] = duration

                atom["data"]["reserved2"] = self.buf.read(8).hex()
                atom["data"]["layer"] = int.from_bytes(self.buf.read(2), "big")
                atom["data"]["alternate_group"] = int.from_bytes(self.buf.read(2), "big")
                atom["data"]["volume"] = int.from_bytes(self.buf.read(2), "big") / 256
                atom["data"]["reserved3"] = self.buf.read(2).hex()
                atom["data"]["matrix"] = self.buf.read(36).hex()
                atom["data"]["width"] = int.from_bytes(self.buf.read(4), "big") / 65536
                atom["data"]["height"] = int.from_bytes(self.buf.read(4), "big") / 65536
        elif typ == "edts":
            atom["data"] = self.read_atom()
        elif typ == "elst":
            version = self.read_version(atom)
            atom["data"]["entries"] = []
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count

            for i in range(0, entry_count):
                if version == 0:
                    segment_duration = int.from_bytes(self.buf.read(4), "big")
                    media_time = int.from_bytes(self.buf.read(4), "big")
                elif version == 1:
                    segment_duration = int.from_bytes(self.buf.read(8), "big")
                    media_time = int.from_bytes(self.buf.read(8), "big")

                if version in (0, 1):
                    entry = {}
                    entry["segment_duration"] = segment_duration
                    entry["media_time"] = media_time
                    entry["media_rate_integer"] = int.from_bytes(self.buf.read(2), "big")
                    entry["media_rate_fraction"] = int.from_bytes(self.buf.read(2), "big")

                    atom["data"]["entries"].append(entry)
        elif typ == "mdhd":
            version = self.read_version(atom)

            if version == 0:
                creation_time = int.from_bytes(self.buf.read(4), "big")
                modification_time = int.from_bytes(self.buf.read(4), "big")
                timescale = int.from_bytes(self.buf.read(4), "big")
                duration = int.from_bytes(self.buf.read(4), "big")
            elif version == 1:
                creation_time = int.from_bytes(self.buf.read(8), "big")
                modification_time = int.from_bytes(self.buf.read(8), "big")
                timescale = int.from_bytes(self.buf.read(4), "big")
                duration = int.from_bytes(self.buf.read(8), "big")

            if version in (0, 1):
                atom["data"]["creation_time"] = mp4_time_to_iso(creation_time)
                atom["data"]["modification_time"] = mp4_time_to_iso(modification_time)
                atom["data"]["timescale"] = timescale
                atom["data"]["duration"] = duration

                atom["data"]["language"] = mp4_decode_mdhd_language(self.buf.read(2))
                atom["data"]["pre_defined"] = self.buf.read(2).hex()
        elif typ == "hdlr":
            self.read_version(atom)
            atom["data"]["pre_defined"] = self.buf.read(4).hex()
            atom["data"]["handler_type"] = self.buf.read(4).decode("utf-8")
            atom["data"]["reserved"] = self.buf.read(12).hex()
            atom["data"]["name"] = self.buf.readunit()[:-1].decode("utf-8")
        elif typ == "vmhd":
            self.read_version(atom)
            atom["data"]["graphicsmode"] = int.from_bytes(self.buf.read(2), "big") 
            atom["data"]["opcolor"] = [int.from_bytes(self.buf.read(2), "big") for _ in range(0, 3)]
        elif typ in ("dref", "stsd"):
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")

            atom["data"]["atoms"] = []
            for i in range(0, entry_count):
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "url ":
            version = self.buf.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.buf.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "local": bool(flags & 1)
            }

            atom["data"]["location"] = self.buf.readunit()[:-1].decode("utf-8")
        elif typ == "avc1":
            atom["data"]["reserved1"] = self.buf.read(6).hex()
            atom["data"]["data_reference_index"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["pre_defined1"] = self.buf.read(2).hex()
            atom["data"]["reserved2"] = self.buf.read(2).hex()
            atom["data"]["pre_defined2"] = self.buf.read(12).hex()
            atom["data"]["width"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["height"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["horizresolution"] = int.from_bytes(self.buf.read(4), "big") / 65536
            atom["data"]["vertresolution"] = int.from_bytes(self.buf.read(4), "big") / 65536
            atom["data"]["reserved3"] = self.buf.read(4).hex()
            atom["data"]["frame_count"] = int.from_bytes(self.buf.read(2), "big")
            l = self.buf.read(1)[0]
            name = self.buf.read(31)
            atom["data"]["compressorname"] = name[:l].decode("utf-8")
            atom["data"]["depth"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["pre_defined3"] = self.buf.read(2).hex()

            self.read_more(atom)
        elif typ == "avcC":
            atom["data"]["configurationVersion"] = self.buf.read(1)[0]
            atom["data"]["AVCProfileIndication"] = self.buf.read(1)[0]
            atom["data"]["profile_compatibility"] = self.buf.read(1)[0]
            atom["data"]["AVCLevelIndication"] = self.buf.read(1)[0]
            atom["data"]["lengthSizeMinusOne"] = self.buf.read(1)[0]

            atom["data"]["numOfSequenceParameterSets"] = self.buf.read(1)[0]
            atom["data"]["sequenceParameterSets"] = []
            for i in range(0, atom["data"]["numOfSequenceParameterSets"] & 0b00011111):
                l = int.from_bytes(self.buf.read(2), "big")
                atom["data"]["sequenceParameterSets"].append(self.buf.read(l).hex())

            atom["data"]["numOfPictureParameterSets"] = self.buf.read(1)[0]
            atom["data"]["pictureParameterSets"] = []
            for i in range(0, atom["data"]["numOfPictureParameterSets"]):
                l = int.from_bytes(self.buf.read(2), "big")
                atom["data"]["pictureParameterSets"].append(self.buf.read(l).hex())
        elif typ == "colr":
            atom["data"]["color_type"] = self.buf.read(4).decode("utf-8")

            match atom["data"]["color_type"]:
                case "nclc":
                    atom["data"]["color_primaries"] = int.from_bytes(self.buf.read(2), "big")
                    atom["data"]["transfer_characteristics"] = int.from_bytes(self.buf.read(2), "big")
                    atom["data"]["matrix_coefficients"] = int.from_bytes(self.buf.read(2), "big")
                case "rICC" | "prof":
                    atom["data"]["icc_profile_data"] = self.buf.readunit().hex()
                case "nclx":
                    atom["data"]["color_primaries"] = int.from_bytes(self.buf.read(2), "big")
                    atom["data"]["transfer_characteristics"] = int.from_bytes(self.buf.read(2), "big")
                    atom["data"]["matrix_coefficients"] = int.from_bytes(self.buf.read(2), "big")
                    full_range_flag = self.buf.read(1)[0]
                    atom["data"]["full_range_flag"] = {
                        "raw": full_range_flag,
                        "full": bool(full_range_flag & 0x80)
                    }
        elif typ == "pasp":
            atom["data"]["hSpacing"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["vSpacing"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "btrt":
            atom["data"]["buffer_size"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["max_bitrate"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["avg_bitrate"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "stts":
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "stss":
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "ctts":
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "stsc":
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "stsz":
            self.read_version(atom)
            atom["data"]["sample_size"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["sample_count"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "stco":
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "sgpd":
            version = self.buf.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.buf.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "variable_length": bool(flags & 1)
            }

            atom["data"]["grouping_type"] = self.buf.read(4).decode("utf-8")

            default_length = 0
            if version == 1 and flags & 1 == 0:
                default_length = int.from_bytes(self.buf.read(4), "big")

            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                length = default_length
                if length == 0:
                    length = int.from_bytes(self.buf.read(4), "big")

                atom["data"]["entries"].append(self.buf.read(length).hex())
        elif typ == "sbgp":
            self.read_version(atom)
            atom["data"]["grouping_type"] = self.buf.read(4).decode("utf-8")

            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                atom["data"]["entries"].append({
                    "sample_count": int.from_bytes(self.buf.read(4), "big"),
                    "group_description_index": int.from_bytes(self.buf.read(4), "big")
                })
        elif typ == "smhd":
            self.read_version(atom)
            atom["data"]["balance"] = int.from_bytes(self.buf.read(2), "big") / 256
            atom["data"]["reserved"] = int.from_bytes(self.buf.read(2), "big")
        elif typ == "mp4a":
            atom["data"]["reserved1"] = self.buf.read(6).hex()
            atom["data"]["data_reference_index"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["reserved2"] = self.buf.read(8).hex()
            atom["data"]["channel_count"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["samplesize"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["pre_defined"] = self.buf.read(2).hex()
            atom["data"]["reserved3"] = self.buf.read(2).hex()
            atom["data"]["samplerate"] = int.from_bytes(self.buf.read(4), "big") / 65536

            self.read_more(atom)
        elif typ == "esds":
            self.read_version(atom)
            atom["data"]["or"] = self.buf.readunit().hex()
        elif typ == "meta":
            self.read_version(atom)
            self.read_more(atom)
        elif typ == "data":
            self.read_version(atom)
            atom["data"]["type"] = int.from_bytes(self.buf.read(4), "big")

            match atom["data"]["type"]:
                case 0:
                    atom["data"]["payload"] = self.buf.readunit().decode("utf-8")
                case 1:
                    atom["data"]["payload"] = self.buf.readunit().decode("utf-16")
                case _:
                    atom["data"]["payload"] = self.buf.readunit().hex()
        elif typ == "free":
            atom["data"]["non-zero"] = sum(self.buf.readunit()) > 0
        elif typ == "co64":
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count
        elif typ == "sdtp":
            self.read_version(atom)
            atom["data"]["sample_dep_type_count"] = len(self.buf.readunit())
        elif typ == "vp09":
            atom["data"]["reserved1"] = self.buf.read(6).hex()
            atom["data"]["data_reference_index"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["pre_defined1"] = self.buf.read(2).hex()
            atom["data"]["reserved2"] = self.buf.read(2).hex()
            atom["data"]["pre_defined2"] = self.buf.read(12).hex()
            atom["data"]["width"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["height"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["horizresolution"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["vertresolution"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["reserved3"] = self.buf.read(4).hex()
            atom["data"]["frame_count"] = int.from_bytes(self.buf.read(2), "big")
            l = self.buf.read(1)[0]
            name = self.buf.read(31)
            atom["data"]["compressorname"] = name[:l].decode("utf-8")
            atom["data"]["depth"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["pre_defined3"] = self.buf.read(2).hex()

            self.read_more(atom)
        elif typ == "vpcC":
            atom["data"]["profile"] = self.buf.read(1)[0]
            atom["data"]["level"] = self.buf.read(1)[0]
            atom["data"]["bit_depth"] = self.buf.read(1)[0]
            atom["data"]["chroma_subsampling"] = self.buf.read(1)[0]
            atom["data"]["video_full_range_flag"] = self.buf.read(1)[0]
            atom["data"]["reserved"] = self.buf.read(3).hex()
        elif typ == "trex":
            self.read_version(atom)
            atom["data"]["track_ID"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["default_sample_description_index"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["default_sample_duration"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["default_sample_size"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["default_sample_flags"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "sidx":
            version = self.read_version(atom)
            atom["data"]["reference_ID"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["earliest_presentation_time"] = int.from_bytes(self.buf.read(4 if version == 0 else 8), "big")
            atom["data"]["first_offset"] = int.from_bytes(self.buf.read(4 if version == 0 else 8), "big")
            atom["data"]["reserved"] = self.buf.read(2).hex()
            atom["data"]["reference_count"] = int.from_bytes(self.buf.read(2), "big")
        elif typ == "mfhd":
            self.read_version(atom)
            atom["data"]["sequence_number"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "tfhd":
            version = self.buf.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.buf.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "base_data_offset_present": bool(flags & 1),
                "sample_description_index_present": bool(flags & 2),
                "default_sample_duration_present": bool(flags & 8),
                "default_sample_size_present": bool(flags & 16),
                "default_sample_flags_present": bool(flags & 32),
                "no_samples": bool(flags & 65536),
                "base_is_moof": bool(flags & 131072)
            }
            atom["data"]["track_ID"] = int.from_bytes(self.buf.read(4), "big")

            if atom["data"]["flags"]["base_data_offset_present"]:
                atom["data"]["base_data_offset"] = int.from_bytes(self.buf.read(8), "big")
            if atom["data"]["flags"]["sample_description_index_present"]:
                atom["data"]["sample_description_index"] = int.from_bytes(self.buf.read(4), "big")
            if atom["data"]["flags"]["default_sample_duration_present"]:
                atom["data"]["default_sample_duration"] = int.from_bytes(self.buf.read(4), "big")
            if atom["data"]["flags"]["default_sample_size_present"]:
                atom["data"]["default_sample_size"] = int.from_bytes(self.buf.read(4), "big")
            if atom["data"]["flags"]["default_sample_flags_present"]:
                atom["data"]["default_sample_flags"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "tfdt":
            version = self.read_version(atom)
            atom["data"]["baseMediaDecodeTime"] = int.from_bytes(self.buf.read(4 if version == 0 else 8), "big")
        elif typ == "trun":
            version = self.buf.read(1)[0]
            atom["data"]["version"] = version
            flags = int.from_bytes(self.buf.read(3), "big")
            atom["data"]["flags"] = {
                "raw": flags,
                "data_offset_present": bool(flags & 1),
                "first_sample_flags_present": bool(flags & 4),
                "sample_duration_present": bool(flags & 256),
                "sample_size_present": bool(flags & 512),
                "sample_flags_present": bool(flags & 1024),
                "sample_composition_time_offsets_present": bool(flags & 2048),
            }
            atom["data"]["sample_count"] = int.from_bytes(self.buf.read(4), "big")
        elif typ == "desc":
            atom["data"]["descriptor"] = self.buf.readunit().hex()
        elif typ == "loci":
            self.read_version(atom)
            atom["data"]["language_code"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["reserved"] = self.buf.read(2).hex()
            atom["data"]["longitude"] = int.from_bytes(self.buf.read(4), "big") / 65536
            atom["data"]["latitude"] = int.from_bytes(self.buf.read(4), "big") / 65536
            atom["data"]["altitude"] = int.from_bytes(self.buf.read(4), "big") / 65536
            atom["data"]["planet"] = self.buf.readunit().split(b"\x00")[0].decode("utf-8")
        elif typ == "hvc1":
            atom["data"]["reserved1"] = self.buf.read(6).hex()
            atom["data"]["data_reference_index"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["pre_defined1"] = self.buf.read(2).hex()
            atom["data"]["reserved2"] = self.buf.read(2).hex()
            atom["data"]["pre_defined2"] = self.buf.read(12).hex()
            atom["data"]["width"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["height"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["horizresolution"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["vertresolution"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["reserved3"] = self.buf.read(4).hex()
            atom["data"]["frame_count"] = int.from_bytes(self.buf.read(2), "big")
            l = self.buf.read(1)[0]
            name = self.buf.read(31)
            atom["data"]["compressorname"] = name[:l].decode("utf-8")
            atom["data"]["depth"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["pre_defined3"] = self.buf.read(2).hex()

            self.read_more(atom)
        elif typ == "hvcC":
            version = self.buf.read(1)[0]
            atom["data"]["version"] = version
            atom["data"]["profile_space,tier_flag,profile_idc"] = self.buf.read(1)[0]
            atom["data"]["profile_compatibility_flags"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["constraint_indicator_flags"] = int.from_bytes(self.buf.read(6), "big")
            atom["data"]["level_idc"] = self.buf.read(1)[0]
            atom["data"]["min_spatial_segmentation_idc"] = int.from_bytes(self.buf.read(2), "big")
            atom["data"]["parallelismType"] = self.buf.read(1)[0]
            atom["data"]["chromaFormat"] = self.buf.read(1)[0]
            atom["data"]["bitDepthLumaMinus8"] = self.buf.read(1)[0]
            atom["data"]["bitDepthChromaMinus8"] = self.buf.read(1)[0]
            atom["data"]["avgFrameRate"] = int.from_bytes(self.buf.read(2), "big") / 256
            atom["data"]["constantFrameRate,numTemporalLayers"] = self.buf.read(1)[0]
            atom["data"]["numOfArrays"] = self.buf.read(1)[0]

            atom["data"]["arrays"] = []
            for i in range(0, atom["data"]["numOfArrays"]):
                array = {}
                array["array_completeness,reserved,NAL_unit_type"] = self.buf.read(1)[0]
                array["numNalus"] = int.from_bytes(self.buf.read(2), "big")
                array["nalus"] = []
                for j in range(0, array["numNalus"]):
                    entry = {}
                    entry["nalUnitLength"] = int.from_bytes(self.buf.read(2), "big")
                    entry["nalUnit"] = self.buf.read(entry["nalUnitLength"]).hex()

                    array["nalus"].append(entry)

                atom["data"]["arrays"].append(array)
        elif typ == "keys":
            self.read_version(atom)
            entry_count = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                l = int.from_bytes(self.buf.read(4), "big")
                ns = self.buf.read(4).decode("utf-8")
                value = self.buf.read(l - 8).decode("utf-8")
                atom["data"]["entries"].append({
                    "namespace": ns,
                    "value": value
                })
        elif typ == "name":
            self.read_version(atom)
            atom["data"]["name"] = self.buf.readunit().decode("utf-8")
        elif typ == "titl":
            self.read_version(atom)
            atom["data"]["reserved1"] = self.buf.read(2).hex()
            atom["data"]["title"] = self.buf.readunit()[:-1].decode("utf-8")
        elif typ == "cslg":
            atom["data"]["compositionToDTSShift"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["leastDecodeToDisplayDelta"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["greatestDecodeToDisplayDelta"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["compositionStartTime"] = int.from_bytes(self.buf.read(4), "big")
            atom["data"]["compositionEndTime"] = int.from_bytes(self.buf.read(4), "big")
        elif typ[0] == "©" or typ == "iods":
            atom["data"]["payload"] = self.buf.readunit().hex()
        elif typ[0] == "\x00" == "mdat":
            pass
        else:
            atom["unknown"] = True

        self.buf.skipunit()
        self.buf.popunit()

        return atom

    def find_stream_type(self, atoms):
        t = None

        for atom in atoms:
            if t != None:
                break

            match atom["type"]:
                case "hvc1":
                    t = "hvec"
                case "avc1":
                    t = "avc1"
                case "vp09":
                    t = "vp9"

            if t == None and "atoms" in atom["data"]:
                t = self.find_stream_type(atom["data"]["atoms"])

        return t

    def find_avcC_length(self, atoms):
        length = None

        for atom in atoms:
            if length != None:
                break

            if atom["type"] == "avcC":
                length = atom["data"]["lengthSizeMinusOne"] & 0x03 + 1

            if length == None and "atoms" in atom["data"]:
                length = self.find_avcC_length(atom["data"]["atoms"])

        return length

    def parse_sei(self, seis):
        while self.buf.unit > 0:
            t = 0
            while True:
                b = self.buf.read(1)[0]
                t += b
                if b != 0xff:
                    break

            l = 0
            while True:
                b = self.buf.read(1)[0]
                l += b
                if b != 0xff:
                    break

            data = self.buf.read(l)
            seis.append({
                "type": t,
                "length": l,
                "data": data.decode("latin-1")
            })

    def parse_mdat_avc1(self, atoms):
        mdat = None
        for atom in atoms:
            if atom["type"] == "mdat":
                mdat = atom

        if mdat == None:
            return

        mdat["data"]["type"] = "avc1"

        nal_length = self.find_avcC_length(atoms)
        if nal_length == None:
            return

        self.buf.seek(mdat["offset"])
        self.buf.setunit(atom["length"])

        self.buf.skip(8)

        mdat["data"]["sei"] = []
        while self.buf.unit > 0:
            length = int.from_bytes(self.buf.read(nal_length), "big")
            if length == 0:
                break

            self.buf.pushunit()
            self.buf.setunit(length - 1)

            t = self.buf.read(1)[0] & 0b00011111

            if t == 6:
                self.parse_sei(mdat["data"]["sei"])

            self.buf.skipunit()
            self.buf.popunit()

        if len(mdat["data"]["sei"]) == 0:
            del mdat["data"]["sei"]

    def parse_mdat(self, atoms):
        stream_type = self.find_stream_type(atoms)
        if stream_type == None:
            return

        match stream_type:
            case "avc1":
                self.parse_mdat_avc1(atoms)
