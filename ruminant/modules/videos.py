import uuid
import struct
import datetime
from .. import module, utils
from . import chew


def mp4_decode_language(lang_bytes):
    lang_code = int.from_bytes(lang_bytes, byteorder="big") & 0x7fff

    c1 = ((lang_code >> 10) & 0x1f) + 0x60
    c2 = ((lang_code >> 5) & 0x1f) + 0x60
    c3 = (lang_code & 0x1f) + 0x60

    return chr(c1) + chr(c2) + chr(c3)


@module.register
class IsoModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(8)[4:] == b"ftyp"

    def chew(self):
        file = {}

        file["type"] = "iso"
        file["atoms"] = []
        while not self.buf.isend():
            file["atoms"].append(self.read_atom())

        with self.buf:
            self.parse_mdat(file["atoms"])

        return file

    def read_version(self, atom):
        version = self.buf.ru8()
        atom["data"]["version"] = version
        atom["data"]["flags"] = self.buf.ru24()
        return version

    def read_more(self, atom):
        atom["data"]["atoms"] = []

        bak = self.buf.backup()

        while self.buf.unit > 8:
            atom["data"]["atoms"].append(self.read_atom())

        self.buf.restore(bak)
        self.buf.skipunit()

    def read_atom(self):
        offset = self.buf.tell()

        length = self.buf.ru32()
        if length == 0:
            pos = self.buf.tell()
            self.buf.seek(0, 2)
            length = self.buf.tell()
            self.buf.seek(pos)
        typ = self.buf.rs(4, "latin-1")

        if length == 1:
            length = self.buf.ru64() - 8

        atom = {"type": typ, "offset": offset, "length": length, "data": {}}

        length -= 8
        self.buf.pushunit()
        self.buf.setunit(length)

        if typ in ("moov", "trak", "mdia", "minf", "dinf", "stbl", "udta",
                   "mvex", "moof", "traf", "gsst", "gstd", "sinf", "schi",
                   "cprt", "trkn", "aART", "iprp", "ipco", "tapt", "tref",
                   "gmhd") or (typ[0] == "©"
                               and self.buf.peek(8)[4:8] == b"data"):
            self.read_more(atom)
        elif typ in ("ftyp", "styp"):
            atom["data"]["major_brand"] = self.buf.rs(4, "utf-8")
            atom["data"]["minor_version"] = self.buf.ru32()
            atom["data"]["compatible_brands"] = []

            while self.buf.unit > 0:
                atom["data"]["compatible_brands"].append(
                    self.buf.rs(4, "utf-8"))
        elif typ == "uuid":
            atom["data"]["uuid"] = str(uuid.UUID(bytes=self.buf.read(16)))
            atom["data"]["user-data"] = self.buf.readunit().decode("utf-8")
            try:
                atom["data"]["user-data"] = utils.xml_to_dict(
                    atom["data"]["user-data"])
            except Exception:
                pass
        elif typ == "mvhd":
            version = self.read_version(atom)

            if version == 0:
                creation_time = self.buf.ru32()
                modification_time = self.buf.ru32()
                timescale = self.buf.ru32()
                duration = self.buf.ru32()
            elif version == 1:
                creation_time = self.buf.ru64()
                modification_time = self.buf.ru64()
                timescale = self.buf.ru32()
                duration = self.buf.ru64()

            if version in (0, 1):
                atom["data"]["creation_time"] = utils.mp4_time_to_iso(
                    creation_time)
                atom["data"]["modification_time"] = utils.mp4_time_to_iso(
                    modification_time)
                atom["data"]["timescale"] = timescale
                atom["data"]["duration"] = duration

                atom["data"]["rate"] = self.buf.rfp32()
                atom["data"]["volume"] = self.buf.rfp16()
                atom["data"]["reserved"] = self.buf.rh(10)
                atom["data"]["matrix"] = self.buf.rh(36)
                atom["data"]["pre_defined"] = self.buf.rh(24)
                atom["data"]["next_track_ID"] = self.buf.ru32()
        elif typ == "tkhd":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            flags = self.buf.ru24()
            atom["data"]["flags"] = {
                "raw": flags,
                "enabled": bool(flags & 1),
                "movie": bool(flags & 2),
                "preview": bool(flags & 4),
            }

            if version == 0:
                creation_time = self.buf.ru32()
                modification_time = self.buf.ru32()
                track_ID = self.buf.ru32()
                reserved1 = self.buf.rh(4)
                duration = self.buf.ru32()

            if version == 1:
                creation_time = self.buf.ru64()
                modification_time = self.buf.ru64()
                track_ID = self.buf.ru32()
                reserved1 = self.buf.rh(4)
                duration = self.buf.ru64()

            if version in (0, 1):
                atom["data"]["creation_time"] = utils.mp4_time_to_iso(
                    creation_time)
                atom["data"]["modification_time"] = utils.mp4_time_to_iso(
                    modification_time)
                atom["data"]["track_ID"] = track_ID
                atom["data"]["reserved1"] = reserved1
                atom["data"]["duration"] = duration

                atom["data"]["reserved2"] = self.buf.rh(8)
                atom["data"]["layer"] = self.buf.ru16()
                atom["data"]["alternate_group"] = self.buf.ru16()
                atom["data"]["volume"] = self.buf.rfp16()
                atom["data"]["reserved3"] = self.buf.rh(2)
                atom["data"]["matrix"] = self.buf.rh(36)
                atom["data"]["width"] = self.buf.rfp32()
                atom["data"]["height"] = self.buf.rfp32()
        elif typ == "edts":
            atom["data"] = self.read_atom()
        elif typ == "elst":
            version = self.read_version(atom)
            atom["data"]["entries"] = []
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count

            for i in range(0, entry_count):
                if version == 0:
                    segment_duration = self.buf.ru32()
                    media_time = self.buf.ru32()
                elif version == 1:
                    segment_duration = self.buf.ru64()
                    media_time = self.buf.ru64()

                if version in (0, 1):
                    entry = {}
                    entry["segment_duration"] = segment_duration
                    entry["media_time"] = media_time
                    entry["media_rate_integer"] = self.buf.ru16()
                    entry["media_rate_fraction"] = self.buf.ru16()

                    atom["data"]["entries"].append(entry)
        elif typ == "mdhd":
            version = self.read_version(atom)

            if version == 0:
                creation_time = self.buf.ru32()
                modification_time = self.buf.ru32()
                timescale = self.buf.ru32()
                duration = self.buf.ru32()
            elif version == 1:
                creation_time = self.buf.ru64()
                modification_time = self.buf.ru64()
                timescale = self.buf.ru32()
                duration = self.buf.ru64()

            if version in (0, 1):
                atom["data"]["creation_time"] = utils.mp4_time_to_iso(
                    creation_time)
                atom["data"]["modification_time"] = utils.mp4_time_to_iso(
                    modification_time)
                atom["data"]["timescale"] = timescale
                atom["data"]["duration"] = duration

                atom["data"]["language"] = mp4_decode_language(
                    self.buf.read(2))
                atom["data"]["pre_defined"] = self.buf.rh(2)
        elif typ == "hdlr":
            self.read_version(atom)
            atom["data"]["pre_defined"] = self.buf.rh(4)
            atom["data"]["handler_type"] = self.buf.rs(4)
            atom["data"]["reserved"] = self.buf.rh(12)
            atom["data"]["name"] = self.buf.readunit().decode("utf-8")
        elif typ == "vmhd":
            self.read_version(atom)
            atom["data"]["graphicsmode"] = self.buf.ru16()
            atom["data"]["opcolor"] = [self.buf.ru16() for _ in range(0, 3)]
        elif typ in ("dref", "stsd"):
            self.read_version(atom)
            entry_count = self.buf.ru32()

            atom["data"]["atoms"] = []
            for i in range(0, entry_count):
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "url ":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            flags = self.buf.ru24()
            atom["data"]["flags"] = {"raw": flags, "local": bool(flags & 1)}

            atom["data"]["location"] = self.buf.readunit()[:-1].decode("utf-8")
        elif typ in ("avc1", "hvc1", "vp09", "encv"):
            atom["data"]["reserved1"] = self.buf.rh(6)
            atom["data"]["data_reference_index"] = self.buf.ru16()
            atom["data"]["pre_defined1"] = self.buf.rh(2)
            atom["data"]["reserved2"] = self.buf.rh(2)
            atom["data"]["pre_defined2"] = self.buf.rh(12)
            atom["data"]["width"] = self.buf.ru16()
            atom["data"]["height"] = self.buf.ru16()
            atom["data"]["horizresolution"] = self.buf.rfp32()
            atom["data"]["vertresolution"] = self.buf.rfp32()
            atom["data"]["reserved3"] = self.buf.rh(4)
            atom["data"]["frame_count"] = self.buf.ru16()
            name_length = self.buf.ru8()
            name = self.buf.read(31)
            atom["data"]["compressorname"] = name[:name_length].decode("utf-8")
            atom["data"]["depth"] = self.buf.ru16()
            atom["data"]["pre_defined3"] = self.buf.rh(2)

            self.read_more(atom)
        elif typ == "avcC":
            atom["data"]["configurationVersion"] = self.buf.ru8()
            atom["data"]["AVCProfileIndication"] = self.buf.ru8()
            atom["data"]["profile_compatibility"] = self.buf.ru8()
            atom["data"]["AVCLevelIndication"] = self.buf.ru8()
            atom["data"]["lengthSizeMinusOne"] = self.buf.ru8()

            atom["data"]["numOfSequenceParameterSets"] = self.buf.ru8()
            atom["data"]["sequenceParameterSets"] = []
            for i in range(
                    0,
                    atom["data"]["numOfSequenceParameterSets"] & 0b00011111):
                length = self.buf.ru16()
                atom["data"]["sequenceParameterSets"].append(
                    self.buf.rh(length))

            atom["data"]["numOfPictureParameterSets"] = self.buf.ru8()
            atom["data"]["pictureParameterSets"] = []
            for i in range(0, atom["data"]["numOfPictureParameterSets"]):
                length = self.buf.ru16()
                atom["data"]["pictureParameterSets"].append(
                    self.buf.rh(length))
        elif typ == "colr":
            atom["data"]["color_type"] = self.buf.rs(4)

            match atom["data"]["color_type"]:
                case "nclc":
                    atom["data"]["color_primaries"] = self.buf.ru16()
                    atom["data"]["transfer_characteristics"] = self.buf.ru16()
                    atom["data"]["matrix_coefficients"] = self.buf.ru16()
                case "rICC" | "prof":
                    atom["data"]["icc_profile_data"] = chew(
                        b"ICC_PROFILE\x00\x00\x00" + self.buf.readunit())
                case "nclx":
                    atom["data"]["color_primaries"] = self.buf.ru16()
                    atom["data"]["transfer_characteristics"] = self.buf.ru16()
                    atom["data"]["matrix_coefficients"] = self.buf.ru16()
                    full_range_flag = self.buf.ru8()
                    atom["data"]["full_range_flag"] = {
                        "raw": full_range_flag,
                        "full": bool(full_range_flag & 0x80),
                    }
        elif typ == "pasp":
            atom["data"]["hSpacing"] = self.buf.ru32()
            atom["data"]["vSpacing"] = self.buf.ru32()
        elif typ == "btrt":
            atom["data"]["buffer_size"] = self.buf.ru32()
            atom["data"]["max_bitrate"] = self.buf.ru32()
            atom["data"]["avg_bitrate"] = self.buf.ru32()
        elif typ == "stts":
            self.read_version(atom)
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count
        elif typ == "stss":
            self.read_version(atom)
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count
        elif typ == "ctts":
            self.read_version(atom)
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count
        elif typ == "stsc":
            self.read_version(atom)
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count
        elif typ == "stsz":
            self.read_version(atom)
            atom["data"]["sample_size"] = self.buf.ru32()
            atom["data"]["sample_count"] = self.buf.ru32()
        elif typ == "stco":
            self.read_version(atom)
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count
        elif typ == "sgpd":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            flags = self.buf.ru24()
            atom["data"]["flags"] = {
                "raw": flags,
                "variable_length": bool(flags & 1),
            }

            atom["data"]["grouping_type"] = self.buf.rs(4)

            default_length = 0
            if version == 1 and flags & 1 == 0:
                default_length = self.buf.ru32()

            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                length = default_length
                if length == 0:
                    length = self.buf.ru32()

                atom["data"]["entries"].append(self.buf.rh(length))
        elif typ == "sbgp":
            self.read_version(atom)
            atom["data"]["grouping_type"] = self.buf.rs(4)

            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                atom["data"]["entries"].append({
                    "sample_count":
                    self.buf.ru32(),
                    "group_description_index":
                    self.buf.ru32(),
                })
        elif typ == "smhd":
            self.read_version(atom)
            atom["data"]["balance"] = self.buf.rfp16()
            atom["data"]["reserved"] = self.buf.ru16()
        elif typ == "mp4a":
            atom["data"]["reserved1"] = self.buf.rh(6)
            atom["data"]["data_reference_index"] = self.buf.ru16()
            atom["data"]["reserved2"] = self.buf.rh(8)
            atom["data"]["channel_count"] = self.buf.ru16()
            atom["data"]["samplesize"] = self.buf.ru16()
            atom["data"]["pre_defined"] = self.buf.rh(2)
            atom["data"]["reserved3"] = self.buf.rh(2)
            atom["data"]["samplerate"] = self.buf.rfp32()

            self.read_more(atom)
        elif typ == "esds":
            self.read_version(atom)
            atom["data"]["or"] = self.buf.readunit().hex()
        elif typ == "data":
            self.read_version(atom)
            atom["data"]["type"] = self.buf.ru32()

            match atom["data"]["type"]:
                case 0:
                    atom["data"]["payload"] = self.buf.readunit().decode(
                        "utf-8")
                case 1:
                    atom["data"]["payload"] = self.buf.readunit().decode(
                        "utf-16")
                case _:
                    atom["data"]["payload"] = self.buf.readunit().hex()
        elif typ == "free":
            atom["data"]["non-zero"] = sum(self.buf.readunit()) > 0
        elif typ == "co64":
            self.read_version(atom)
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count
        elif typ == "sdtp":
            self.read_version(atom)
            atom["data"]["sample_dep_type_count"] = len(self.buf.readunit())
        elif typ == "vpcC":
            atom["data"]["profile"] = self.buf.ru8()
            atom["data"]["level"] = self.buf.ru8()
            atom["data"]["bit_depth"] = self.buf.ru8()
            atom["data"]["chroma_subsampling"] = self.buf.ru8()
            atom["data"]["video_full_range_flag"] = self.buf.ru8()
            atom["data"]["reserved"] = self.buf.rh(3)
        elif typ == "trex":
            self.read_version(atom)
            atom["data"]["track_ID"] = self.buf.ru32()
            atom["data"]["default_sample_description_index"] = self.buf.ru32()
            atom["data"]["default_sample_duration"] = self.buf.ru32()
            atom["data"]["default_sample_size"] = self.buf.ru32()
            atom["data"]["default_sample_flags"] = self.buf.ru32()
        elif typ == "sidx":
            version = self.read_version(atom)
            atom["data"]["reference_ID"] = self.buf.ru32()
            atom["data"]["earliest_presentation_time"] = int.from_bytes(
                self.buf.read(4 if version == 0 else 8), "big")
            atom["data"]["first_offset"] = int.from_bytes(
                self.buf.read(4 if version == 0 else 8), "big")
            atom["data"]["reserved"] = self.buf.rh(2)
            atom["data"]["reference_count"] = self.buf.ru16()
        elif typ == "mfhd":
            self.read_version(atom)
            atom["data"]["sequence_number"] = self.buf.ru32()
        elif typ == "tfhd":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            flags = self.buf.ru24()
            atom["data"]["flags"] = {
                "raw": flags,
                "base_data_offset_present": bool(flags & 1),
                "sample_description_index_present": bool(flags & 2),
                "default_sample_duration_present": bool(flags & 8),
                "default_sample_size_present": bool(flags & 16),
                "default_sample_flags_present": bool(flags & 32),
                "no_samples": bool(flags & 65536),
                "base_is_moof": bool(flags & 131072),
            }
            atom["data"]["track_ID"] = self.buf.ru32()

            if atom["data"]["flags"]["base_data_offset_present"]:
                atom["data"]["base_data_offset"] = self.buf.ru64()
            if atom["data"]["flags"]["sample_description_index_present"]:
                atom["data"]["sample_description_index"] = self.buf.ru32()
            if atom["data"]["flags"]["default_sample_duration_present"]:
                atom["data"]["default_sample_duration"] = self.buf.ru32()
            if atom["data"]["flags"]["default_sample_size_present"]:
                atom["data"]["default_sample_size"] = self.buf.ru32()
            if atom["data"]["flags"]["default_sample_flags_present"]:
                atom["data"]["default_sample_flags"] = self.buf.ru32()
        elif typ == "tfdt":
            version = self.read_version(atom)
            atom["data"]["baseMediaDecodeTime"] = int.from_bytes(
                self.buf.read(4 if version == 0 else 8), "big")
        elif typ == "trun":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            flags = self.buf.ru24()
            atom["data"]["flags"] = {
                "raw": flags,
                "data_offset_present": bool(flags & 1),
                "first_sample_flags_present": bool(flags & 4),
                "sample_duration_present": bool(flags & 256),
                "sample_size_present": bool(flags & 512),
                "sample_flags_present": bool(flags & 1024),
                "sample_composition_time_offsets_present": bool(flags & 2048),
            }
            atom["data"]["sample_count"] = self.buf.ru32()
        elif typ == "desc":
            atom["data"]["descriptor"] = self.buf.readunit().hex()
        elif typ == "loci":
            self.read_version(atom)
            atom["data"]["language_code"] = self.buf.ru16()
            atom["data"]["reserved"] = self.buf.rh(2)
            atom["data"]["longitude"] = self.buf.rfp32()
            atom["data"]["latitude"] = self.buf.rfp32()
            atom["data"]["altitude"] = self.buf.rfp32()
            atom["data"]["planet"] = (
                self.buf.readunit().split(b"\x00")[0].decode("utf-8"))
        elif typ == "hvcC":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            atom["data"]["profile_space,tier_flag,profile_idc"] = (
                self.buf.ru8())
            atom["data"]["profile_compatibility_flags"] = self.buf.ru32()
            atom["data"]["constraint_indicator_flags"] = int.from_bytes(
                self.buf.read(6), "big")
            atom["data"]["level_idc"] = self.buf.ru8()
            atom["data"]["min_spatial_segmentation_idc"] = self.buf.ru16()
            atom["data"]["parallelismType"] = self.buf.ru8()
            atom["data"]["chromaFormat"] = self.buf.ru8()
            atom["data"]["bitDepthLumaMinus8"] = self.buf.ru8()
            atom["data"]["bitDepthChromaMinus8"] = self.buf.ru8()
            atom["data"]["avgFrameRate"] = self.buf.rfp16()
            atom["data"]["constantFrameRate,numTemporalLayers"] = (
                self.buf.ru8())
            atom["data"]["numOfArrays"] = self.buf.ru8()

            atom["data"]["arrays"] = []
            for i in range(0, atom["data"]["numOfArrays"]):
                array = {}
                array["array_completeness,reserved,NAL_unit_type"] = (
                    self.buf.ru8())
                array["numNalus"] = self.buf.ru16()
                array["nalus"] = []
                for j in range(0, array["numNalus"]):
                    entry = {}
                    entry["nalUnitLength"] = self.buf.ru16()
                    entry["nalUnit"] = self.buf.rh(entry["nalUnitLength"])

                    array["nalus"].append(entry)

                atom["data"]["arrays"].append(array)
        elif typ == "keys":
            self.read_version(atom)
            entry_count = self.buf.ru32()
            atom["data"]["entry_count"] = entry_count

            atom["data"]["entries"] = []
            for i in range(0, entry_count):
                length = self.buf.ru32()
                ns = self.buf.rs(4)
                value = self.buf.rs(length - 8)
                atom["data"]["entries"].append({
                    "namespace": ns,
                    "value": value
                })
        elif typ == "name":
            self.read_version(atom)
            atom["data"]["name"] = self.buf.readunit().decode("utf-8")
        elif typ == "titl":
            self.read_version(atom)
            atom["data"]["reserved1"] = self.buf.rh(2)
            atom["data"]["title"] = self.buf.readunit()[:-1].decode("utf-8")
        elif typ == "cslg":
            atom["data"]["compositionToDTSShift"] = self.buf.ru32()
            atom["data"]["leastDecodeToDisplayDelta"] = self.buf.ru32()
            atom["data"]["greatestDecodeToDisplayDelta"] = self.buf.ru32()
            atom["data"]["compositionStartTime"] = self.buf.ru32()
            atom["data"]["compositionEndTime"] = self.buf.ru32()
        elif typ == "senc":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            flags = self.buf.ru24()
            atom["data"]["flags"] = {
                "raw": flags,
                "use-subsample-encryption": bool(flags & 2)
            }
            atom["data"]["sample-count"] = self.buf.ru32()
        elif typ == "frma":
            atom["data"]["original-media-type"] = self.buf.rs(4)
        elif typ == "schm":
            version = self.buf.ru8()
            atom["data"]["version"] = version
            flags = self.buf.ru24()
            atom["data"]["flags"] = {"raw": flags, "has-uri": bool(flags & 1)}
            atom["data"]["type"] = self.buf.rs(4)
            atom["data"]["version"] = f"{self.buf.ru16()}.{self.buf.ru16()}"
            if flags & 1:
                atom["data"]["uri"] = self.buf.readunit().decode("utf-8")
        elif typ == "tenc":
            version = self.read_version(atom)

            atom["data"]["reserved"] = self.buf.rh(1 if version != 0 else 2)

            if version >= 1:
                atom["data"]["encrypted-blocks-per-pattern"] = self.buf.ru32()
                atom["data"]["clear-blocks-per-pattern"] = self.buf.ru32()

            atom["data"]["is-encrypted"] = self.buf.ru8()
            atom["data"]["iv-size"] = self.buf.ru8()
            atom["data"]["key-id"] = self.buf.rh(16)

            if atom["data"]["is-encrypted"] == 1 and atom["data"][
                    "iv-size"] == 0:
                constant_iv_size = self.buf.ru8()
                atom["data"]["constant-iv-size"] = constant_iv_size
                atom["data"]["constant-iv"] = self.buf.rh(constant_iv_size)
        elif typ == "mehd":
            version = self.read_version(atom)
            atom["data"]["fragment-duration"] = self.buf.ru32(
            ) if version == 0 else self.buf.ru64()
        elif typ == "pssh":
            version = self.read_version(atom)

            system_id = self.buf.ruuid()
            atom["data"]["system-id"] = system_id
            atom["data"]["system-name"] = {
                "29701fe4-3cc7-4a34-8c5b-ae90c7439a47": "Netflix FairPlay",
                "9a04f079-9840-4286-ab92-e65be0885f95": "PlayReady",
                "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed": "Widevine",
                "6dd8b3c3-45f4-4a68-bf3a-64168d01a4a6": "ABV DRM (MoDRM)",
                "f239e769-efa3-4850-9c16-a903c6932efb":
                "Adobe Primetime DRM version 4",
                "616c7469-6361-7374-2d50-726f74656374": "Alticast",
                "94ce86fb-07ff-4f43-adb8-93d2fa968ca2": "FairPlay",
                "279fe473-512c-48fe-ade8-d176fee6b40f": "Arris Titanium",
                "3d5e6d35-9b9a-41e8-b843-dd3c6e72c42c": "ChinaDRM",
                "3ea8778f-7742-4bf9-b18b-e834b2acbd47": "Clear Key AES-128",
                "be58615b-19c4-4684-88b3-c8c57e99e957": "Clear Key SAMPLE-AES",
                "e2719d58-a985-b3c9-781a-b030af78d30e": "Clear Key DASH-IF",
                "644fe7b5-260f-4fad-949a-0762ffb054b4": "CMLA (OMA DRM)",
                "37c33258-7b99-4c7e-b15d-19af74482154":
                "Commscope Titanium V3",
                "45d481cb-8fe0-49c0-ada9-ab2d2455b2f2": "CoreCrypt",
                "dcf4e3e3-62f1-5818-7ba6-0a6fe33ff3dd": "DigiCAP SmartXess",
                "35bf197b-530e-42d7-8b65-1b4bf415070f": "DivX DRM Series 5",
                "80a6be7e-1448-4c37-9e70-d5aebe04c8d2":
                "Irdeto Content Protection",
                "5e629af5-38da-4063-8977-97ffbd9902d4":
                "Marlin Adaptive Streaming Simple Profile V1.0",
                "6a99532d-869f-5922-9a91-113ab7b1e2f3": "MobiTV DRM",
                "adb41c24-2dbf-4a6d-958b-4457c0d27b95":
                "Nagra MediaAccess PRM 3.0",
                "1f83e1e8-6ee9-4f0d-ba2f-5ec4e3ed1a66": "SecureMedia",
                "992c46e6-c437-4899-b6a0-50fa91ad0e39":
                "SecureMedia SteelKnot",
                "a68129d3-575b-4f1a-9cba-3223846cf7c3":
                "Synamedia/Cisco/NDS VideoGuard DRM",
                "aa11967f-cc01-4a4a-8e99-c5d3dddfea2d": "Unitend DRM (UDRM)",
                "9a27dd82-fde2-4725-8cbc-4234aa06ec09": "Verimatrix VCAS",
                "b4413586-c58c-ffb0-94a5-d4896c1af6c3":
                "Viaccess-Orca DRM (VODRM)",
                "793b7956-9f94-4946-a942-23e7ef7e44b4": "VisionCrypt",
                "1077efec-c0b2-4d02-ace3-3c1e52e2fb4b": "W3C Common PSSH box",
            }.get(system_id, "Unknown")

            if version == 1:
                key_id_count = self.buf.ru32()
                atom["data"]["key-id-count"] = key_id_count

                atom["data"]["key-ids"] = []
                for i in range(0, key_id_count):
                    atom["data"]["key-ids"].append(self.buf.ruuid())

            blob_length = self.buf.ru32()
            atom["data"]["blob-length"] = blob_length

            self.buf.pushunit()
            self.buf.setunit(blob_length)

            match system_id:
                case "9a04f079-9840-4286-ab92-e65be0885f95":
                    self.buf.skip(4)
                    record_count = self.buf.ru16l()
                    atom["data"]["record-count"] = record_count

                    atom["data"]["records"] = []
                    for i in range(0, record_count):
                        record = {}
                        record_type = self.buf.ru16l()
                        record["type"] = record_type
                        record_length = self.buf.ru16l()
                        record["length"] = record_length

                        content = self.buf.read(record_length)
                        match record_type:
                            case 1:
                                record["data"] = utils.xml_to_dict(
                                    content.decode("utf16"))
                            case _:
                                record["data"] = content.hex()

                        atom["data"]["records"].append(record)
                case "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
                    atom["data"]["blob"] = {}

                    for i, t, v in utils.read_protobuf(self.buf, blob_length):
                        match i:
                            case 1:
                                atom["data"]["blob"]["algorithm"] = {
                                    "raw": v,
                                    "name": {
                                        0: "Unencrypted",
                                        1: "AES-CTR"
                                    }.get(v, "Unknown")
                                }
                            case 2:
                                if "key-ids" not in atom["data"]["blob"]:
                                    atom["data"]["blob"]["key-ids"] = []

                                atom["data"]["blob"]["key-ids"].append(
                                    utils.to_uuid(v))
                            case 3:
                                atom["data"]["blob"]["provider"] = v.decode(
                                    "utf-8")
                            case 4:
                                atom["data"]["blob"][
                                    "content-id"] = utils.to_uuid(v)
                            case 6:
                                atom["data"]["blob"]["policy"] = v.decode(
                                    "utf-8")
                            case 7:
                                atom["data"]["blob"]["crypto-period-index"] = v
                            case 8:
                                atom["data"]["blob"][
                                    "grouped-license"] = v.hex()
                            case 9:
                                atom["data"]["blob"]["protection-scheme"] = {
                                    "raw": v,
                                    "name": {
                                        0: "Unspecified (CENC)",
                                        1667591779: "CENC",
                                        1667392305: "CBC1",
                                        1667591795: "CENS",
                                        1667392371: "CBCS",
                                    }.get(v, "Unknown")
                                }
                case _:
                    atom["data"]["blob"] = self.buf.rh(blob_length)

            self.buf.skipunit()
            self.buf.popunit()
        elif typ == "pitm":
            version = self.read_version(atom)
            atom["data"]["item-id"] = self.buf.ru32(
            ) if version > 0 else self.buf.ru16()
        elif typ == "iloc":
            version = self.read_version(atom)

            temp = self.buf.ru8()
            offset_size = temp >> 4
            atom["data"]["offset-size"] = offset_size
            length_size = temp & 0x0f
            atom["data"]["length-size"] = length_size
            temp = self.buf.ru8()
            base_offset_size = temp >> 4
            atom["data"]["base-offset-size"] = base_offset_size
            index_size = temp & 0x0f
            atom["data"]["index-size"] = index_size

            item_count = self.buf.ru32() if version >= 2 else self.buf.ru16()
            atom["data"]["item-count"] = item_count

            atom["data"]["items"] = []
            for i in range(0, item_count):
                item = {}
                item["id"] = self.buf.ru32(
                ) if version >= 2 else self.buf.ru16()

                if version > 0:
                    temp = self.buf.ru16()
                    item["construction-method"] = temp & 0x0f
                    item["reserved"] = temp >> 4

                item["data-reference-index"] = self.buf.ru16()
                base_offset = int.from_bytes(self.buf.read(base_offset_size),
                                             "big")
                item["base-offset"] = base_offset

                extent_count = self.buf.ru16()
                item["extent-count"] = extent_count

                item["extents"] = []
                for j in range(0, extent_count):
                    extent = {}

                    if version > 0 and index_size > 0:
                        extent["index"] = int.from_bytes(
                            self.buf.read(index_size), "big")

                    extent["offset"] = int.from_bytes(
                        self.buf.read(offset_size), "big")
                    extent["length"] = int.from_bytes(
                        self.buf.read(length_size), "big")

                    item["extents"].append(extent)

                atom["data"]["items"].append(item)
        elif typ == "iinf":
            version = self.read_version(atom)
            entry_count = self.buf.ru16() if version < 1 else self.buf.ru32()
            atom["data"]["item-count"] = entry_count

            atom["data"]["items"] = []
            for i in range(0, entry_count):
                atom["data"]["items"].append(self.read_atom())

        elif typ == "infe":
            version = self.read_version(atom)
            if version < 2:
                atom["data"]["id"] = self.buf.ru16()
                atom["data"]["protection-index"] = self.buf.ru16()
                atom["data"]["name"] = self.buf.rzs()
                atom["data"]["type"] = self.buf.rzs()
                atom["data"]["encoding"] = self.buf.rzs()

            if version == 1:
                extension_type = self.buf.rs(4)
                atom["data"]["extension-type"] = extension_type
                if extension_type == "fdel":
                    atom["data"]["extension"] = {}
                    atom["data"]["extension"][
                        "content-location"] = self.buf.rzs()
                    atom["data"]["extension"]["content-md5"] = self.buf.rzs()
                    atom["data"]["extension"][
                        "content-length"] = self.buf.ru64()
                    atom["data"]["extension"][
                        "transfer-length"] = self.buf.ru64()
                    count = self.buf.ru8()
                    atom["data"]["extension"]["entry-count"] = count
                    atom["data"]["extension"]["entries"] = [
                        self.buf.ru32() for j in range(0, count)
                    ]

            if version >= 2:
                atom["data"]["id"] = self.buf.ru16(
                ) if version == 2 else self.buf.ru32()
                atom["data"]["protection-index"] = self.buf.ru16()
                item_type = self.buf.rs(4)
                atom["data"]["type"] = item_type
                atom["data"]["name"] = self.buf.rzs()

                match item_type:
                    case "mime":
                        atom["data"]["content-type"] = self.buf.rzs()
                        atom["data"]["content-encoding"] = self.buf.rzs()
                    case "uri ":
                        atom["data"]["uri-type"] = self.buf.rzs()
        elif typ == "ispe":
            version = self.read_version(atom)
            atom["data"]["width"] = self.buf.ru32()
            atom["data"]["height"] = self.buf.ru32()
        elif typ == "pixi":
            version = self.read_version(atom)
            channel_count = self.buf.ru8()
            atom["data"]["channel-count"] = channel_count
            atom["data"]["channel-bit-depths"] = [
                self.buf.ru8() for i in range(0, channel_count)
            ]
        elif typ == "av1C":
            temp = self.buf.ru8()
            atom["data"]["version"] = temp & 0x7f
            temp = self.buf.ru8()
            atom["data"]["seq-profile"] = temp >> 5
            atom["data"]["seq-level-idx-0"] = temp & 0x1f
            temp = self.buf.ru8()
            atom["data"]["seq-tier-0"] = bool(temp & 0x80)
            atom["data"]["high-bitdepth"] = bool(temp & 0x40)
            atom["data"]["twelve-bit"] = bool(temp & 0x20)
            atom["data"]["monochrome"] = bool(temp & 0x10)
            atom["data"]["chroma-subsampling-x"] = bool(temp & 0x08)
            atom["data"]["chroma-subsampling-y"] = bool(temp & 0x04)
            atom["data"]["chroma-sample-poisition"] = temp & 0x03
            temp = self.buf.ru8()
            atom["data"]["reserved"] = temp >> 5
            atom["data"]["initial-presentation-delay-present"] = bool(temp
                                                                      & 0x10)
            atom["data"]["initial-presentation-delay-minus-one"] = temp & 0x0f
        elif typ == "ipma":
            version = self.read_version(atom)
            item_count = self.buf.ru32() if version > 0 else self.buf.ru16()
            atom["data"]["item-count"] = item_count

            atom["data"]["items"] = []
            for i in range(0, item_count):
                item = {}
                item["id"] = self.buf.ru32() if version > 0 else self.buf.ru16(
                )
                association_count = self.buf.ru8()
                item["association-count"] = association_count

                item["associations"] = []
                for j in range(0, association_count):
                    association = {}
                    if atom["data"]["flags"] & 1:
                        entry = self.buf.ru16()
                        association["essential"] = bool(entry & 0x8000)
                        association["index"] = entry & 0x7fff
                    else:
                        entry = self.buf.ru8()
                        association["essential"] = bool(entry & 0x80)
                        association["index"] = entry & 0x7f

                    item["associations"].append(association)

                atom["data"]["items"].append(item)
        elif typ == "mebx":
            atom_count = self.buf.ru64()
            atom["data"]["atom-count"] = atom_count

            atom["data"]["atoms"] = []
            for i in range(0, atom_count):
                atom["data"]["atoms"].append(self.read_atom())
        elif typ == "ilst":
            atom["entries"] = []
            while self.buf.unit:
                length = self.buf.ru32()
                atom["entries"].append({
                    "id": self.buf.ru32(),
                    "content": self.read_atom()
                })
        elif typ in ("clef", "prof", "enof"):
            self.read_version(atom)
            atom["data"]["width"] = self.buf.rfp32()
            atom["data"]["height"] = self.buf.rfp32()
        elif typ == "alis":
            self.read_version(atom)
            atom["data"]["name"] = self.buf.rzs()
        elif typ == "mpvd":
            with self.buf.subunit():
                atom["data"]["content"] = chew(self.buf)
        elif typ == "meta":
            if self.buf.pu32() == 0:
                self.buf.skip(4)

            self.read_more(atom)
        elif typ == "iref":
            version = self.read_version(atom)

            atom["data"]["from"] = self.buf.ru16(
            ) if version == 0 else self.buf.ru32()
            atom["data"]["reference-count"] = self.buf.ru16()
        elif typ == "idat":
            atom["data"]["length"] = self.buf.unit
        elif typ == "irot":
            atom["data"]["value"] = self.buf.ru8()
        elif typ == "smta":
            self.read_version(atom)
            self.read_more(atom)
        elif typ == "mdln":
            atom["data"]["model-name"] = self.buf.rs(self.buf.unit)
        elif typ == "sefd":
            # algorithm is from https://github.com/eilam-ashbell/seft-parser/blob/4083f85aad99e01af014d089bf0b0d42acf27ad4/lib/esm/classes/Seft.js  # noqa: E501
            with self.buf.sub(self.buf.unit):
                length = self.buf.available()

                self.buf.seek(length - 8)
                headers_block_length = self.buf.ru32l()
                headers_block_start_offset = length - (headers_block_length +
                                                       8)
                self.buf.seek(headers_block_start_offset + 4)
                atom["data"]["seft-version"] = self.buf.ru32l()
                record_count = self.buf.ru32l()
                atom["data"]["record-count"] = record_count

                atom["data"]["records"] = []
                for i in range(0, record_count):
                    record = {}
                    record["padding"] = self.buf.ru16l()
                    record["type"] = self.buf.ru16l()
                    offset = self.buf.ru32l()
                    record["offset"] = offset
                    record_length = self.buf.ru32l()
                    record["length"] = record_length
                    record["content"] = {}

                    with self.buf:
                        self.buf.seek(headers_block_start_offset - offset)
                        record["content"]["padding"] = self.buf.ru16l()
                        record["content"]["type"] = self.buf.ru16l()
                        key_length = self.buf.ru32l()
                        record["content"]["key-length"] = key_length
                        value_length = record_length - key_length - 8
                        record["content"]["value-length"] = value_length
                        record["content"]["name"] = self.buf.rs(key_length)
                        record["content"]["value"] = self.buf.rs(
                            value_length, "latin-1")

                    atom["data"]["records"].append(record)
        elif typ == "clap":
            atom["data"]["clean-aperture-width"] = self.buf.ru32(
            ) / self.buf.ru32()
            atom["data"]["clean-aperture-height"] = self.buf.ru32(
            ) / self.buf.ru32()
            atom["data"]["horiz-off"] = self.buf.ru32() / self.buf.ru32()
            atom["data"]["vert-off"] = self.buf.ru32() / self.buf.ru32()
        elif typ == "gmin":
            self.read_version(atom)
            atom["data"]["graphicsmode"] = self.buf.ru16()
            atom["data"]["opcolor"] = [self.buf.ru16() for _ in range(0, 3)]
            atom["data"]["balance"] = self.buf.ru16()
            atom["data"]["reserved"] = self.buf.rh(2)
        elif typ[0] == "©" or typ in ("iods", "SDLN", "smrd"):
            atom["data"]["payload"] = self.buf.readunit().decode("latin-1")
        elif typ in ("hint", "cdsc", "font", "hind", "vdep", "vplx", "subt",
                     "cdep"):
            atom["data"]["track-id"] = self.buf.ru32()
        elif typ in ("lpcm"):
            # TODO
            pass
        elif typ[0] == "\x00" or typ in ("mdat", "wide"):
            pass
        else:
            atom["unknown"] = True

        self.buf.skipunit()
        self.buf.popunit()

        return atom

    def find_stream_type(self, atoms):
        t = None

        for atom in atoms:
            if t is not None:
                break

            match atom["type"]:
                case "hvc1":
                    t = "hvec"
                case "avc1":
                    t = "avc1"
                case "vp09":
                    t = "vp9"

            if t is None and "atoms" in atom["data"]:
                t = self.find_stream_type(atom["data"]["atoms"])

        return t

    def find_avcC_length(self, atoms):
        length = None

        for atom in atoms:
            if length is not None:
                break

            if atom["type"] == "avcC":
                length = atom["data"]["lengthSizeMinusOne"] & 0x03 + 1

            if length is None and "atoms" in atom["data"]:
                length = self.find_avcC_length(atom["data"]["atoms"])

        return length

    def parse_sei(self, seis):
        while self.buf.unit > 0:
            t = 0
            while True:
                b = self.buf.ru8()
                t += b
                if b != 0xff:
                    break

            l = 0
            while True:
                b = self.buf.ru8()
                l += b
                if b != 0xff:
                    break

            data = self.buf.read(l)
            sei = {
                "type": t,
                "length": l,
            }

            if data[:16].hex() == "dc45e9bde6d948b7962cd820d923eeef":
                sei["data"] = {
                    "uuid": data[:16].hex(),
                    "libx264-banner": data[16:-1].decode("utf-8"),
                }
            else:
                sei["data"] = data.decode("latin-1")

            seis.append(sei)

    def parse_mdat_avc1(self, atoms):
        mdat = None
        for atom in atoms:
            if atom["type"] == "mdat":
                mdat = atom

        if mdat is None:
            return

        mdat["data"]["type"] = "avc1"

        nal_length = self.find_avcC_length(atoms)
        if nal_length is None:
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

            t = self.buf.ru8() & 0b00011111

            if t == 6:
                self.parse_sei(mdat["data"]["sei"])

            self.buf.skipunit()
            self.buf.popunit()

        if len(mdat["data"]["sei"]) == 0:
            del mdat["data"]["sei"]

    def parse_mdat(self, atoms):
        stream_type = self.find_stream_type(atoms)
        if stream_type is None:
            return

        try:
            match stream_type:
                case "avc1":
                    self.parse_mdat_avc1(atoms)
        except Exception:
            # sei parsing can fail with cenc extensions
            pass


@module.register
class MatroskaModule(module.RuminantModule):
    FIELDS = {
        0x1a45dfa3: ("EMBL", "master"),
        0x18538067: ("Segment", "master"),
        0x4286: ("EBMLVersion", "uint"),
        0x42f7: ("EBMLReadVersion", "uint"),
        0x42f2: ("EBMLMaxIDLength", "uint"),
        0x42f3: ("EBMLMaxSizeLength", "uint"),
        0x4282: ("DocType", "ascii"),
        0x4287: ("DocTypeVersion", "uint"),
        0x4285: ("DocTypeReadVersion", "uint"),
        0x114d9b74: ("SeekHead", "master"),
        0x4dbb: ("Seek", "master"),
        0x53ab: ("SeekID", "hex"),
        0x53ac: ("SeekPosition", "uint"),
        0x1549a966: ("Info", "master"),
        0x1654ae6b: ("Tracks", "master"),
        0x1254c367: ("Tags", "master"),
        0x1f43b675: ("Cluster", "skipped-master"),
        0x2ad7b1: ("TimestampScale", "uint"),
        0x1c53bb6b: ("Cues", "master"),
        0x67: ("Timestamp", "uint"),
        0x27: ("Position", "uint"),
        0x4d80: ("MuxingApp", "utf8"),
        0x5741: ("WritingApp", "utf8"),
        0x73a4: ("SegmentUUID", "uuid"),
        0x4489: ("Duration", "float"),
        0xbf: ("CRC-32", "hex"),
        0xae: ("TrackEntry", "master"),
        0xec: ("Void", "blob"),
        0xd7: ("TrackNumber", "uint"),
        0x73c5: ("TrackUID", "uint"),
        0x9c: ("FlagLacing", "uint"),
        0x22b59c: ("Language", "utf8"),
        0x86: ("CodecID", "ascii"),
        0x83: ("TrackType", "uint"),
        0x23e383: ("DefaultDuration", "uint"),
        0xe0: ("Video", "master"),
        0x55ee: ("MaxBlockAdditionID", "uint"),
        0xb0: ("PixelWidth", "uint"),
        0xba: ("PixelHeight", "uint"),
        0x9a: ("FlagInterlaced", "uint"),
        0x55b0: ("Colour", "master"),
        0x55ba: ("TransferCharacteristics", "uint"),
        0x55b1: ("MatrixCoefficients", "uint"),
        0x55bb: ("Primaries", "uint"),
        0x55b9: ("Range", "uint"),
        0x55b7: ("ChromaSitingHorz", "uint"),
        0x55b8: ("ChromaSitingVert", "uint"),
        0x63a2: ("CodecPrivate", "binary"),
        0x56aa: ("CodecDelay", "uint"),
        0x56bb: ("SeekPreRoll", "uint"),
        0xe1: ("Audio", "master"),
        0x9f: ("Channels", "uint"),
        0xb5: ("SamplingFrequency", "float"),
        0x6264: ("BitDepth", "uint"),
        0x7373: ("Tag", "master"),
        0xe7: ("Timestamp", "uint"),
        0xa3: ("SimpleBlock", "binary"),
        0x63c0: ("Targets", "master"),
        0x67c8: ("SimpleTarget", "master"),
        0x45a3: ("TagName", "utf8"),
        0x4487: ("TagString", "utf8"),
        0x63c5: ("TagTrackUID", "uint"),
        0xa0: ("BlockGroup", "master"),
        0xa1: ("Block", "binary"),
        0x75a2: ("DiscardPadding", "sint"),
        0xbb: ("CuePoint", "master"),
        0xb3: ("CueTime", "uint"),
        0xb7: ("CueTrackPositions", "master"),
        0xf7: ("CueTrack", "uint"),
        0xf1: ("CueClusterPosition", "uint"),
        0xf0: ("CueRelativePosition", "uint")
    }

    def identify(buf):
        return buf.peek(4) == b"\x1a\x45\xdf\xa3"

    def chew(self):
        meta = {}
        meta["type"] = "matroska"

        meta["tags"] = []
        while self.buf.available():
            meta["tags"].append(self.read_tag())

        return meta

    def read_vint(self, m=True):
        val = self.buf.ru8()

        mask = 0x80
        length = 1
        while length <= 8 and not (val & mask):
            mask >>= 1
            length += 1

        if length > 8:
            raise ValueError("VINT too long")

        if m:
            val &= (mask - 1)
        for _ in range(length - 1):
            val <<= 8
            val |= self.buf.ru8()

        return val

    def read_tag(self):
        tag_id = self.read_vint(False)
        tag_length = self.read_vint()

        tag = {}
        tag["name"], tag["type"] = self.FIELDS.get(
            tag_id, (f"Unknown ({hex(tag_id)})", "unknown"))

        tag["length"] = tag_length

        self.buf.pushunit()
        self.buf.setunit(tag_length)

        match tag["type"]:
            case "sint":
                tag["data"] = int.from_bytes(self.buf.readunit(),
                                             "big",
                                             signed=True)
            case "uint":
                tag["data"] = int.from_bytes(self.buf.readunit(), "big")
            case "float":
                match tag_length:
                    case 0:
                        tag["data"] = 0.0
                    case 4:
                        tag["data"] = struct.unpack(">f", self.buf.read(4))[0]
                    case 8:
                        tag["data"] = struct.unpack(">d", self.buf.read(8))[0]
                    case _:
                        raise ValueError(f"Invalid float size {tag_length}")
            case "ascii":
                tag["data"] = self.buf.rs(tag_length, "ascii")
            case "utf8":
                tag["data"] = self.buf.rs(tag_length, "utf-8")
            case "date":
                tag["data"] = (datetime.datetime(
                    2001, 1, 1, tzinfo=datetime.timezone.utc) +
                               datetime.timedelta(microseconds=int.from_bytes(
                                   self.buf.readunit(), "big", signed=True) /
                                                  1000)).isoformat()
            case "master":
                if tag_length == 0:
                    self.buf.popunit()
                    self.buf.pushunit()

                tag["data"] = []
                while self.buf.unit > 0:
                    tag["data"].append(self.read_tag())
            case "hex":
                tag["data"] = self.buf.rh(tag_length)
            case "uuid":
                tag["data"] = utils.to_uuid(self.buf.read(tag_length))

        self.buf.skipunit()
        self.buf.popunit()

        return tag
