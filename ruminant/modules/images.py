import zlib
import datetime
from . import chew
from .. import module, utils


@module.register
class IPTCIIMModule(module.RuminantModule):
    RESOURCE_IDS = {
        1000: "Number of channels, rows, columns, depth, and mode (obsolete)",
        1001: "Macintosh print manager print info record",
        1002: "Macintosh page format information (obsolete)",
        1003: "Indexed color table (obsolete)",
        1005: "Resolution info (obsolete)",
        1006: "Names of alpha channels",
        1007: "Display info (obsolete)",
        1008: "Caption string",
        1009: "Border information",
        1010: "Background color",
        1011: "Print flags",
        1012: "Grayscale/multichannel halftoning info",
        1013: "Color halftoning info",
        1014: "Duotone halftoning info",
        1015: "Grayscale/multichannel transfer function",
        1016: "Color transfer functions",
        1017: "Duotone transfer functions",
        1018: "Duotone image info",
        1019: "Effective black and white values",
        1021: "EPS options",
        1022: "Quick mask info",
        1024: "Layer state info",
        1025: "Working path",
        1026: "Layers group info",
        1028: "IPTC-NAA record",
        1029: "Image mode for JPEG",
        1030: "JPEG quality",
        1032: "Grid and guides",
        1033: "Thumbnail (raw RGB)",
        1034: "Copyright flag",
        1035: "URL",
        1036: "Thumbnail (JPEG compressed)",
        1037: "Global angle",
        1038: "Color samplers resource (obsolete)",
        1039: "ICC profile",
        1040: "Watermark",
        1041: "ICC untagged profile",
        1042: "Effects visible",
        1043: "Spot Halftone",
        1044: "Document-specific IDs seed number",
        1045: "Unicode alpha names",
        1046: "Indexed color table count",
        1047: "Transparency index",
        1049: "Global altitude",
        1050: "Slices",
        1051: "Workflow URL",
        1052: "Jump to XPEP",
        1053: "Alpha identifiers",
        1054: "URL list",
        1057: "Version info",
        1058: "EXIF data",
        1059: "EXIF data",
        1060: "XMP metadata",
        1061: "Caption digest",
        1062: "Print scale",
        1064: "Pixel aspect ratio",
        1065: "Layer comps",
        1066: "Alternate duotone colors",
        1067: "Alternate spot colors",
        1069: "Layer selection ID(s)",
        1070: "HDR toning information",
        1071: "Print info",
        1072: "Layer group(s) enabled ID",
        1073: "Color samplers resource",
        1074: "Measurement scale",
        1075: "Timeline information",
        1076: "Sheet disclosure",
        1077: "Display info",
        1078: "Onion skins",
        1080: "Count information",
        1082: "Print information",
        1083: "Print style",
        1084: "Macintosh NSPrintInfo",
        1085: "Windows DEVMODE",
        1086: "Auto save file path",
        1087: "Auto save format",
        1088: "Path selection state",
        2999: "Name of clipping path",
        3000: "Origin path info",
        7000: "Image Ready variables",
        7001: "Image Ready data sets",
        7002: "Image Ready default selected state",
        7003: "Image Ready 7 rollover expanded state",
        7004: "Image Ready rollover expanded state",
        7005: "Image Ready save layer settings",
        7006: "Image Ready version",
        8000: "Lightroom workflow",
        10000: "Print flags information",
    }

    for i in range(2000, 2998):
        RESOURCE_IDS[i] = "Path information"

    for i in range(4000, 5000):
        RESOURCE_IDS[i] = "Plug-In resource(s)"

    COLOR_SPACES = {
        0: "RGB",
        1: "HSB",
        2: "CMYK",
        7: "Lab",
        8: "Grayscale",
        9: "Wide CMYK",
        10: "HSL",
        11: "HSB (Alt)",
        12: "Multichannel",
        13: "Duotone",
        14: "Lab (Alt)",
    }

    # not vetted yet, could be horribly wrong
    RECORD_DATASET_NAMES = {
        1: {
            0: "Model Version",
            5: "Destination",
            20: "File Format",
            22: "File Format Version",
            30: "Service Identifier",
            40: "Envelope Number",
            50: "Product ID",
            60: "Envelope Priority",
            70: "Date Sent",
            80: "Time Sent",
            90: "Coded Character Set",
            100: "UNO (Unique Name of Object)",
            120: "ARM Identifier",
            122: "ARM Version"
        },
        2: {
            3: "Object Type Reference",
            5: "Object Name",
            7: "Edit Status",
            8: "Editorial Update",
            10: "Urgency",
            12: "Subject Reference",
            15: "Category",
            20: "Supplemental Category",
            22: "Fixture Identifier",
            25: "Keywords",
            26: "Content Location Code",
            27: "Content Location Name",
            30: "Release Date",
            35: "Release Time",
            37: "Expiration Date",
            38: "Expiration Time",
            40: "Special Instructions",
            42: "Action Advised",
            45: "Reference Service",
            47: "Reference Date",
            50: "Reference Number",
            55: "Date Created",
            60: "Time Created",
            62: "Digital Creation Date",
            63: "Digital Creation Time",
            65: "Originating Program",
            70: "Program Version",
            75: "Object Cycle",
            80: "By-line",
            85: "By-line Title",
            90: "City",
            92: "Sublocation",
            95: "Province/State",
            100: "Country/Primary Location Code",
            101: "Country/Primary Location Name",
            103: "Original Transmission Reference",
            105: "Headline",
            110: "Credit",
            115: "Source",
            116: "Copyright Notice",
            118: "Contact",
            120: "Caption/Abstract",
            122: "Caption Writer/Editor",
            130: "Image Type",
            131: "Image Orientation",
            135: "Language Identifier",
            150: "Audio Type",
            151: "Audio Sampling Rate",
            152: "Audio Sampling Resolution",
            153: "Audio Duration",
            154: "Audio Outcue",
            184: "Job ID",
            185: "Master Document ID",
            186: "Short Document ID",
            187: "Unique Document ID",
            188: "Owner ID"
        },
        3: {
            0: "Record Version",
            10: "Picture Number",
            20: "Pixels Per Line",
            30: "Number Of Lines",
            40: "Pixel Size In Scanning Direction",
            50: "Pixel Size Perpendicular To Scanning Direction",
            55: "Supplement Type",
            60: "Colour Representation",
            64: "Interchange Colour Space",
            65: "Colour Sequence",
            66: "ICC Input Colour Profile",
            70: "Colour Calibration Matrix Table",
            80: "Lookup Table",
            84: "Number Of Index Entries",
            85: "Colour Palette",
            86: "Number Of Bits Per Sample",
            90: "Sampling Structure",
            100: "Scanning Direction",
            102: "Image Rotation",
            110: "Data Compression Method",
            120: "Quantisation Method",
            125: "End Points",
            130: "Excursion Tolerance",
            135: "Bits Per Component",
            140: "Maximum Density Range",
            145: "Gamma Compensated Value"
        }
    }

    def identify(buf):
        return buf.peek(18) == b"Photoshop 3.0\x008BIM"

    def chew(self):
        meta = {}
        meta["type"] = "iptc-iim"
        meta["data"] = {}

        self.buf.skip(14)

        meta["data"]["blocks"] = []
        while self.buf.available():
            header = self.buf.read(4)
            assert header == b"8BIM", f"Invalid IRB block header: {header}"
            block = {}

            resource_id = self.buf.ru16()
            block["resource-id"] = (
                self.RESOURCE_IDS.get(resource_id, "Unknown") +
                f" (0x{hex(resource_id)[2:].zfill(4)})")
            name_length = self.buf.ru8()
            block["resource-name"] = self.buf.rs(name_length)
            if name_length % 2 == 0:
                self.buf.skip(1)

            data_length = self.buf.ru32()
            block["data-length"] = data_length

            self.buf.setunit((data_length + 1) & 0xfffffffe)

            block["data"] = {}
            try:
                match resource_id:
                    case 1036:
                        block["data"]["format"] = self.buf.ru32()
                        block["data"]["width"] = self.buf.ru32()
                        block["data"]["height"] = self.buf.ru32()
                        block["data"]["width-bytes"] = self.buf.ru32()
                        block["data"]["total-size"] = self.buf.ru32()
                        block["data"]["compressed-size"] = self.buf.ru32()
                        block["data"]["bit-depth"] = self.buf.ru16()
                        block["data"]["planes"] = self.buf.ru16()

                        with self.buf.sub(block["data"]["compressed-size"]):
                            block["data"]["image"] = chew(self.buf)
                    case 1005:
                        block["data"]["horizontal-dpi"] = self.buf.rfp32()
                        horizontal_unit = self.buf.ru16()
                        block["data"]["horizontal-unit"] = {
                            "raw": horizontal_unit,
                            "name": {
                                1: "inches",
                                2: "centimeters",
                                3: "points",
                                4: "picas",
                                5: "columns",
                            }.get(horizontal_unit, "unknown"),
                        }
                        block["data"]["horizontal-scale"] = self.buf.ru16()

                        block["data"]["vertical-dpi"] = self.buf.rfp32()
                        vertical_unit = self.buf.ru16()
                        block["data"]["vertical-unit"] = {
                            "raw": vertical_unit,
                            "name": {
                                1: "Inches",
                                2: "Centimeters",
                                3: "Points",
                                4: "Picas",
                                5: "Columns",
                            }.get(vertical_unit, "Unknown"),
                        }
                        block["data"]["vertical-scale"] = self.buf.ru16()
                    case 1010:
                        color_space = self.buf.ru16()
                        block["data"]["color-space"] = {
                            "raw": color_space,
                            "name":
                            self.COLOR_SPACES.get(color_space, "Unknown"),
                        }
                        block["data"]["components"] = [
                            self.buf.ru16() for _ in range(0, 4)
                        ]
                    case 1011:
                        flags = self.buf.ru16()
                        block["data"]["flags"] = {
                            "raw": flags,
                            "show-image": bool(flags & 1),
                        }
                    case 1037:
                        block["data"]["angle"] = self.buf.ru32()
                    case 1044:
                        block["data"]["seed"] = self.buf.rh(4)
                    case 1049:
                        block["data"]["altitude"] = self.buf.ru32()
                    case 1028:
                        self.buf.skip(1)
                        record_number = self.buf.ru8()
                        block["data"]["record-number"] = {
                            "raw": record_number,
                            "name": {
                                1: "Envelope Record",
                                2: "Application Record",
                                3: "Pre‑ObjectData Descriptor Record",
                                4: "ObjectData Descriptor Record",
                                5: "Pre‑Data Descriptor Record",
                                6: "Data Descriptor Record",
                                7: "Pre‑ObjectData Descriptor Record",
                                8: "Object Record",
                                9: "Post‑Object Descriptor Record"
                            }.get(record_number, "Unknown")
                        }

                        dataset_number = self.buf.ru8()
                        block["data"]["dataset-number"] = {
                            "raw":
                            dataset_number,
                            "name":
                            self.RECORD_DATASET_NAMES.get(record_number,
                                                          {}).get(
                                                              dataset_number,
                                                              "Unknown")
                        }

                        data_length = self.buf.ru16()
                        block["data"]["data-length"] = data_length
                        block["data"]["data"] = self.buf.rs(
                            data_length, "latin-1")
                    case 1061:
                        block["data"]["digest"] = self.buf.rh(16)
                    case _:
                        block["data"]["unknown"] = True
            except Exception:
                block["data"]["malformed"] = True

            meta["data"]["blocks"].append(block)
            self.buf.skipunit()
            self.buf.resetunit()

        return meta


@module.register
class ICCProfileModule(module.RuminantModule):

    def read_tag(self, offset, length):
        tag = {}

        with self.buf:
            self.buf.seek(offset)
            typ = self.buf.rs(4)
            self.buf.skip(4)
            self.buf.setunit(length - 8)

            tag["data"] = {}
            tag["data"]["type"] = typ
            match typ:
                case "text":
                    tag["data"]["string"] = self.buf.readunit()[:-1].decode(
                        "ascii")
                case "desc":
                    desc_length = self.buf.ru32()
                    tag["data"]["string"] = self.buf.rs(
                        desc_length - 1, "ascii")
                case "XYZ ":
                    tag["data"]["x"] = self.buf.rsfp32()
                    tag["data"]["y"] = self.buf.rsfp32()
                    tag["data"]["z"] = self.buf.rsfp32()
                case "curv":
                    tag["data"]["curve-entry-count"] = self.buf.ru32()
                case "view":
                    tag["data"]["illuminant"] = {
                        "x": self.buf.rsfp32(),
                        "y": self.buf.rsfp32(),
                        "z": self.buf.rsfp32(),
                    }
                    tag["data"]["surround"] = {
                        "x": self.buf.rsfp32(),
                        "y": self.buf.rsfp32(),
                        "z": self.buf.rsfp32(),
                    }
                    illuminant_type = self.buf.ru32()
                    tag["data"]["illuminant-type"] = {
                        "raw": illuminant_type,
                        "name": {
                            0: "Unknown",
                            1: "D50",
                            2: "D65",
                            3: "D93",
                            4: "F2",
                            5: "D55",
                            6: "A",
                            7: "Equi-Power (E)",
                            8: "F8",
                        }.get(illuminant_type, "Unknown"),
                    }
                case "meas":
                    standard_observer = self.buf.ru32()
                    tag["data"]["standard-observer"] = {
                        "raw": standard_observer,
                        "name": {
                            0: "Unknown",
                            1: "CIE 1931 standard colorimetric observer",
                            2: "CIE 1964 standard colorimetric observer",
                        }.get(standard_observer, "Unknown"),
                    }
                    tag["data"]["measurement-backing"] = {
                        "x": self.buf.rsfp32(),
                        "y": self.buf.rsfp32(),
                        "z": self.buf.rsfp32(),
                    }
                    measurement_geometry = self.buf.ru32()
                    tag["data"]["measurement-geometry"] = {
                        "raw": measurement_geometry,
                        "name": {
                            0: "Unknown",
                            1: "0°:45° or 45°:0°",
                            2: "0°:d or d:0°",
                        }.get(measurement_geometry, "Unknown"),
                    }
                    tag["data"]["measurement-flare"] = self.buf.rfp32()
                    standard_illuminant = self.buf.ru32()
                    tag["data"]["standard-illuminant"] = {
                        "raw": standard_illuminant,
                        "name": {
                            0: "Unknown",
                            1: "D50",
                            2: "D65",
                            3: "D93",
                            4: "F2",
                            5: "D55",
                            6: "A",
                            7: "Equi-Power (E)",
                            8: "F8",
                        }.get(standard_illuminant, "Unknown"),
                    }
                case "sig ":
                    tag["data"]["signature"] = self.buf.rs(4)
                case "mluc":
                    record_count = self.buf.ru32()
                    tag["data"]["record-count"] = record_count
                    record_size = self.buf.ru32()
                    tag["data"]["record-size"] = record_size

                    tag["data"]["records"] = []
                    for i in range(0, record_count):
                        record = {}
                        record["language-code"] = self.buf.rs(2)
                        record["country-code"] = self.buf.rs(2)
                        record["length"] = self.buf.ru32()
                        record["offset"] = self.buf.ru32()

                        with self.buf:
                            self.buf.resetunit()
                            self.buf.seek(record["offset"] + offset)
                            record["text"] = self.buf.rs(
                                record["length"], "utf-16be")

                        tag["data"]["records"].append(record)
                case "para":
                    function_type = self.buf.ru16()
                    tag["data"]["function-type"] = function_type
                    self.buf.skip(2)

                    tag["data"]["params"] = {}
                    g = self.buf.rsfp32()
                    tag["data"]["params"]["g"] = g
                    if function_type > 0:
                        a = self.buf.rsfp32()
                        tag["data"]["params"]["a"] = a
                        b = self.buf.rsfp32()
                        tag["data"]["params"]["b"] = b
                    if function_type > 1:
                        c = self.buf.rsfp32()
                        tag["data"]["params"]["c"] = c
                    if function_type > 2:
                        d = self.buf.rsfp32()
                        tag["data"]["params"]["d"] = d
                    if function_type > 3:
                        e = self.buf.rsfp32()
                        tag["data"]["params"]["e"] = e
                        f = self.buf.rsfp32()
                        tag["data"]["params"]["f"] = f

                    tag["data"]["formula"] = {}
                    match function_type:
                        case 0:
                            tag["data"]["formula"][
                                f"X >= {-b / a}"] = f"Y = X ^ {g}"
                            tag["data"]["formula"][
                                f"X < {-b / a}"] = f"Y = X ^ {g}"
                        case 1:
                            tag["data"]["formula"][
                                f"X >= {-b / a}"] = f"Y = ({a} * X + {b}) ^ {g}"
                            tag["data"]["formula"][f"X < {-b / a}"] = "Y = 0"
                        case 2:
                            tag["data"]["formula"][
                                f"X >= {d}"] = f"Y = ({a} * X + {b}) ^ {g} + {c}"
                            tag["data"]["formula"][
                                f"X < {-b / a}"] = f"Y = {c}"
                        case 3:
                            tag["data"]["formula"][
                                f"X >= {d}"] = f"Y = ({a} * X + {b}) ^ {g}"
                            tag["data"]["formula"][
                                f"X < {-b / a}"] = f"Y = {c} * X"
                        case 4:
                            tag["data"]["formula"][
                                f"X >= {d}"] = f"Y = ({a} * X + {b}) ^ {g} + {c}"
                            tag["data"]["formula"][
                                f"X < {-b / a}"] = f"Y = {c} * X + {f}"
                        case _:
                            tag["data"]["formula"]["X >= ?"] = "Y = ?"
                            tag["data"]["formula"]["X < ?"] = "Y = ?"
                case "ucmI":
                    tag["data"]["parameter-length"] = self.buf.ru32()
                    tag["data"][
                        "engine-version"] = f"{self.buf.ru8()}.{self.buf.ru8()}.{self.buf.ru16()}"  # noqa: E501
                    tag["data"][
                        "profile-format-document-version"] = f"{self.buf.ru8()}.{self.buf.ru8()}.{self.buf.ru16()}"  # noqa: E501
                    tag["data"][
                        "profile-version"] = f"{self.buf.ru8()}.{self.buf.ru8()}.{self.buf.ru16()}"  # noqa: E501
                    tag["data"]["profile-build-number"] = self.buf.ru32()
                    tag["data"]["interpolation-flag"] = self.buf.ru32()
                    tag["data"]["atob0-tag-override"] = self.buf.ru32()
                    tag["data"]["atob1-tag-override"] = self.buf.ru32()
                    tag["data"]["atob2-tag-override"] = self.buf.ru32()
                    tag["data"]["btoa0-tag-override"] = self.buf.ru32()
                    tag["data"]["btoa1-tag-override"] = self.buf.ru32()
                    tag["data"]["btoa2-tag-override"] = self.buf.ru32()
                    tag["data"]["preview0-tag-override"] = self.buf.ru32()
                    tag["data"]["preview1-tag-override"] = self.buf.ru32()
                    tag["data"]["preview2-tag-override"] = self.buf.ru32()
                    tag["data"]["gamut-tag-override"] = self.buf.ru32()
                    tag["data"]["atob0-tag-optimization-flag"] = self.buf.ru32(
                    )
                    tag["data"]["atob1-tag-optimization-flag"] = self.buf.ru32(
                    )
                    tag["data"]["atob2-tag-optimization-flag"] = self.buf.ru32(
                    )
                    tag["data"]["btoa0-tag-optimization-flag"] = self.buf.ru32(
                    )
                    tag["data"]["btoa1-tag-optimization-flag"] = self.buf.ru32(
                    )
                    tag["data"]["btoa2-tag-optimization-flag"] = self.buf.ru32(
                    )
                    tag["data"][
                        "preview0-tag-optimization-flag"] = self.buf.ru32()
                    tag["data"][
                        "preview1-tag-optimization-flag"] = self.buf.ru32()
                    tag["data"][
                        "preview2-tag-optimization-flag"] = self.buf.ru32()
                    tag["data"]["gamut-tag-optimization-flag"] = self.buf.ru32(
                    )
                    tag["data"]["creator-division"] = self.buf.rs(
                        64, "latin-1").rstrip("\x00")
                    tag["data"]["support-division"] = self.buf.rs(
                        64, "latin-1").rstrip("\x00")
                    tag["data"]["von-kries-flag"] = self.buf.ru32()
                case _:
                    tag["data"]["unkown"] = True

        return tag

    def identify(buf):
        return buf.peek(12) == b"ICC_PROFILE\x00"

    def chew(self):
        meta = {}
        meta["type"] = "icc-profile"
        meta["data"] = {}

        self.buf.skip(14)
        length = self.buf.ru32()
        meta["data"]["length"] = length
        self.buf.setunit(length - 4)

        meta["data"]["cmm-type"] = self.buf.rs(4)
        meta["data"][
            "version"] = f"{self.buf.ru8()}.{self.buf.rh(3).rstrip('0')}"
        meta["data"]["class"] = self.buf.rs(4)
        meta["data"]["color-space"] = self.buf.rs(4)
        meta["data"]["profile-connection-space"] = self.buf.rs(4)
        year, month, day, hour, minute, second = [
            self.buf.ru16() for _ in range(0, 6)
        ]
        meta["data"]["date"] = (str(year).zfill(4) + "-" +
                                str(month).zfill(2) + "-" + str(day).zfill(2) +
                                "T" + str(hour).zfill(2) + ":" +
                                str(minute).zfill(2) + ":" +
                                str(second).zfill(2))
        meta["data"]["file-signature"] = self.buf.rs(4)
        meta["data"]["platform"] = self.buf.rs(4)
        meta["data"]["flags"] = self.buf.rh(4)
        meta["data"]["device-manufacturer"] = self.buf.rs(4)
        meta["data"]["device-model"] = self.buf.rs(4)
        meta["data"]["device-attributes"] = self.buf.rh(8)
        render_intent = self.buf.ru32()
        meta["data"]["render-intent"] = {
            "raw": render_intent,
            "name": {
                0: "Perceptual",
                1: "Relative Colorimetric",
                2: "Saturation",
                3: "Absolute Colorimetric",
            }.get(render_intent, "Unknown"),
        }
        meta["data"]["pcs-illuminant"] = [
            self.buf.rsfp32() for _ in range(0, 3)
        ]
        meta["data"]["profile-creator"] = self.buf.rs(4)
        meta["data"]["profile-id"] = self.buf.rh(4)
        meta["data"]["reserved"] = self.buf.rh(40)

        tag_count = self.buf.ru32()
        meta["data"]["tag-count"] = tag_count
        meta["data"]["tags"] = []
        for i in range(0, tag_count):
            tag = {}
            tag["name"] = self.buf.rs(4)
            tag["offset"] = self.buf.ru32()
            tag["length"] = self.buf.ru32()

            tag |= self.read_tag(tag["offset"] + 14, tag["length"])

            meta["data"]["tags"].append(tag)

        self.buf.readunit()

        return meta


@module.register
class JPEGModule(module.RuminantModule):
    HAS_PAYLOAD = [
        0xc0,  # SOF0: Baseline DCT
        0xc1,  # SOF1: Extended sequential DCT
        0xc2,  # SOF2: Progressive DCT
        0xc3,  # SOF3: Lossless sequential
        0xc5,  # SOF5: Differential sequential DCT
        0xc6,  # SOF6: Differential progressive DCT
        0xc7,  # SOF7: Differential lossless
        0xc9,  # SOF9: Extended sequential, arithmetic coding
        0xca,  # SOF10: Progressive, arithmetic coding
        0xcb,  # SOF11: Lossless, arithmetic coding
        0xcd,  # SOF13: Differential sequential, arithmetic coding
        0xce,  # SOF14: Differential progressive, arithmetic coding
        0xcf,  # SOF15: Differential lossless, arithmetic coding
        0xc4,  # DHT: Define Huffman Table
        0xdb,  # DQT: Define Quantization Table
        0xdd,  # DRI: Define Restart Interval
        0xda,  # SOS: Start of Scan
        0xe0,  # APP0
        0xe1,  # APP1
        0xe2,  # APP2
        0xe3,  # APP3
        0xe4,  # APP4
        0xe5,  # APP5
        0xe6,  # APP6
        0xe7,  # APP7
        0xe8,  # APP8
        0xe9,  # APP9
        0xea,  # APP10
        0xeb,  # APP11
        0xec,  # APP12
        0xed,  # APP13
        0xee,  # APP14
        0xef,  # APP15
        0xfe,  # COM: Comment
        0xf0,  # JPG0 (JPEG extensions, reserved)
        0xf1,  # JPG1
        0xf2,  # JPG2
        0xf3,  # JPG3
        0xf4,  # JPG4
        0xf5,  # JPG5
        0xf6,  # JPG6
        0xf7,  # JPG7
        0xf8,  # JPG8
        0xf9,  # JPG9
        0xfa,  # JPG10
        0xfb,  # JPG11
        0xfc,  # JPG12
        0xfd,  # JPG13
    ]

    MARKER_NAME = {
        0xd8: "SOI",
        0xd9: "EOI",
        0xc0: "SOF0",
        0xc1: "SOF1",
        0xc2: "SOF2",
        0xc3: "SOF3",
        0xc5: "SOF5",
        0xc6: "SOF6",
        0xc7: "SOF7",
        0xc9: "SOF9",
        0xca: "SOF10",
        0xcb: "SOF11",
        0xcd: "SOF13",
        0xce: "SOF14",
        0xcf: "SOF15",
        0xc4: "DHT",
        0xdb: "DQT",
        0xdd: "DRI",
        0xda: "SOS",
        0xfe: "COM",
        0xe0: "APP0",
        0xe1: "APP1",
        0xe2: "APP2",
        0xe3: "APP3",
        0xe4: "APP4",
        0xe5: "APP5",
        0xe6: "APP6",
        0xe7: "APP7",
        0xe8: "APP8",
        0xe9: "APP9",
        0xea: "APP10",
        0xeb: "APP11",
        0xec: "APP12",
        0xed: "APP13",
        0xee: "APP14",
        0xef: "APP15",
        0xf0: "JPG0",
        0xf1: "JPG1",
        0xf2: "JPG2",
        0xf3: "JPG3",
        0xf4: "JPG4",
        0xf5: "JPG5",
        0xf6: "JPG6",
        0xf7: "JPG7",
        0xf8: "JPG8",
        0xf9: "JPG9",
        0xfa: "JPG10",
        0xfb: "JPG11",
        0xfc: "JPG12",
        0xfd: "JPG13",
        0xd0: "RST0",
        0xd1: "RST1",
        0xd2: "RST2",
        0xd3: "RST3",
        0xd4: "RST4",
        0xd5: "RST5",
        0xd6: "RST6",
        0xd7: "RST7",
        0x01: "TEM",
    }

    def identify(buf):
        return buf.peek(3) == b"\xff\xd8\xff"

    def chew(self):
        meta = {}
        meta["type"] = "jpeg"

        meta["chunks"] = []
        should_break = False
        while self.buf.available() and not should_break:
            chunk = {}

            assert self.buf.ru8() == 0xff, "wrong marker prefix"
            typ = self.buf.ru8()
            chunk["type"] = (self.MARKER_NAME.get(typ, "UNK") +
                             f" (0x{hex(typ)[2:].zfill(2)})")

            if typ in self.HAS_PAYLOAD:
                length = self.buf.ru16() - 2
            else:
                length = 0

            self.buf.pushunit()
            self.buf.setunit(length)
            chunk["length"] = length

            chunk["data"] = {}
            if typ == 0xe0 and self.buf.peek(5) == b"JFIF\x00":
                self.buf.skip(5)
                chunk["data"]["version"] = (str(self.buf.ru8()) + "." +
                                            str(self.buf.ru8()))
                units = self.buf.ru8()
                chunk["data"]["units"] = {
                    "raw": units,
                    "name": {
                        0: "No units",
                        1: "Pixels per inch",
                        2: "Pixels per centimeter",
                    }.get(units, "Unknown"),
                }
                chunk["data"]["horizontal-pixel-density"] = self.buf.ru16()
                chunk["data"]["vertical-pixel-density"] = self.buf.ru16()
                chunk["data"]["thumbnail-width"] = self.buf.ru8()
                chunk["data"]["thumbnail-height"] = self.buf.ru8()
                chunk["data"]["thumbnail-data-length"] = self.buf.unit
            elif typ == 0xe1 and self.buf.peek(6) == b"Exif\x00\x00":
                self.buf.skip(6)
                with self.buf.subunit():
                    chunk["data"]["tiff"] = chew(self.buf)
            elif typ == 0xe1 and self.buf.peek(4) == b"http":
                raw = False

                with self.buf:
                    try:
                        ns = b""
                        while self.buf.peek(1)[0]:
                            ns += self.buf.read(1)
                        self.buf.skip(1)
                        ns = ns.decode("utf-8")

                        if ns == "http://ns.adobe.com/xmp/extension/":
                            self.buf.skip(40)

                        xmp = utils.xml_to_dict(
                            self.buf.readunit().decode("utf-8"))
                        chunk["data"]["namespace"] = ns
                        chunk["data"]["xmp"] = xmp
                    except Exception:
                        raw = True

                if raw:
                    chunk["data"]["payload"] = self.buf.readunit().decode(
                        "latin-1")
            elif typ == 0xe2 and self.buf.peek(12) == b"ICC_PROFILE\x00":
                with self.buf.subunit():
                    chunk["data"]["icc-profile"] = chew(self.buf)
            elif typ == 0xec and self.buf.peek(5) == b"Ducky":
                self.buf.skip(5)

                ducky_type = self.buf.ru16()
                chunk["data"]["ducky-type"] = {
                    1: "Quality",
                    2: "Comment",
                    3: "Copyright"
                }.get(ducky_type,
                      "Unknown") + f" (0x{hex(ducky_type)[2:].zfill(4)})"

                match ducky_type:
                    case 1:
                        self.buf.skip(2)
                        chunk["data"]["value"] = self.buf.ru32()
                    case 2 | 3:
                        length = self.buf.ru32()
                        chunk["data"]["value"] = self.buf.rs(length)
                    case _:
                        chunk["data"]["value"] = self.buf.readunit().hex()
                        chunk["data"]["unknown"] = True
            elif typ == 0xed and self.buf.peek(18) == b"Photoshop 3.0\x008BIM":
                with self.buf.subunit():
                    chunk["data"]["iptc"] = chew(self.buf)
            elif typ == 0xed and self.buf.peek(9) == b"Adobe_CM\x00":
                self.buf.skip(9)
                chunk["data"]["adobe-cm-payload"] = self.buf.readunit().hex()
            elif typ == 0xee and self.buf.peek(5) == b"Adobe":
                chunk["data"]["identifier"] = self.buf.rs(5)
                chunk["data"]["pre-defined"] = self.buf.rh(1)
                chunk["data"]["flags0"] = self.buf.rh(2)
                chunk["data"]["flags1"] = self.buf.rh(2)
                chunk["data"]["transform"] = self.buf.ru8()
            elif typ & 0xf0 == 0xe0:
                chunk["data"]["payload"] = self.buf.readunit().hex()
            elif typ == 0xc0:
                chunk["data"]["sample-precision"] = self.buf.ru8()
                chunk["data"]["height"] = self.buf.ru16()
                chunk["data"]["width"] = self.buf.ru16()
                component_count = self.buf.ru8()
                chunk["data"]["component-count"] = component_count
                chunk["data"]["components"] = []
                for i in range(0, component_count):
                    component = {}

                    component["id"] = self.buf.ru8()

                    sampling_factors = self.buf.ru8()
                    component["sampling-factors"] = {
                        "raw": sampling_factors,
                        "horizontal": (sampling_factors & 0xf0) >> 4,
                        "vertical": sampling_factors & 0x0f,
                    }

                    component["quantization-table-id"] = self.buf.ru8()

                    chunk["data"]["components"].append(component)
            elif typ == 0xda:
                component_count = self.buf.ru8()
                chunk["data"]["component-count"] = component_count
                chunk["data"]["components"] = []
                for i in range(0, component_count):
                    component = {}

                    component["id"] = self.buf.ru8()

                    huffman_table_selector = self.buf.ru8()
                    component["huffman-table-selector"] = {
                        "raw": huffman_table_selector,
                        "dc": (huffman_table_selector & 0xf0) >> 4,
                        "ac": huffman_table_selector & 0x0f,
                    }

                    chunk["data"]["components"].append(component)

                chunk["data"]["spectral-selection-start"] = self.buf.ru8()
                chunk["data"]["spectral-selection-end"] = self.buf.ru8()
                chunk["data"]["successive-approximation"] = self.buf.ru8()

                image_length = self.buf.tell()
                self.buf.resetunit()
                self.buf.search(b"\xff\xd9")
                self.buf.setunit(0)

                chunk["data"]["image-length"] = self.buf.tell() - image_length
            elif typ == 0xd9:
                should_break = True

            meta["chunks"].append(chunk)

            self.buf.skipunit()
            self.buf.popunit()

        return meta


@module.register
class PNGModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(8) == b"\x89PNG\r\n\x1a\n"

    def chew(self):
        meta = {}
        meta["type"] = "png"

        self.buf.seek(8)
        meta["chunks"] = []
        while self.buf.available():
            length = self.buf.ru32()
            self.buf.pushunit()
            self.buf.setunit(length + 4)

            chunk_type = self.buf.read(4)

            chunk = {
                "chunk-type": chunk_type.decode("utf-8"),
                "length": length,
                "flags": {
                    "critical": chunk_type[0] & 32 == 0,
                    "private": chunk_type[1] & 32 == 1,
                    "conforming": chunk_type[2] & 32 == 0,
                    "safe-to-copy": chunk_type[3] & 32 == 1,
                },
            }

            data = self.buf.peek(length + 4)
            data, crc = data[:-4], data[-4:]
            target_crc = zlib.crc32(chunk_type + data)

            chunk["crc"] = {
                "value": crc.hex(),
                "correct": int.from_bytes(crc, "big") == target_crc
                & 0xffffffff,
            }

            if not chunk["crc"]["correct"]:
                chunk["crc"]["actual"] = target_crc.to_bytes(4, "big").hex()

            chunk["data"] = {}
            match chunk_type.decode("latin-1"):
                case "IHDR":
                    chunk["data"]["width"] = self.buf.ru32()
                    chunk["data"]["height"] = self.buf.ru32()
                    chunk["data"]["bit-depth"] = self.buf.ru8()
                    chunk["data"]["color-type"] = self.buf.ru8()
                    chunk["data"]["compression"] = self.buf.ru8()
                    chunk["data"]["filter-method"] = self.buf.ru8()
                    chunk["data"]["interlace-method"] = self.buf.ru8()
                case "eXIf":
                    with self.buf.sub(length):
                        chunk["data"]["tiff"] = chew(self.buf)
                case "pHYs":
                    chunk["data"]["width-pixels-per-unit"] = self.buf.ru32()
                    chunk["data"]["height-pixels-per-unit"] = self.buf.ru32()
                    unit = self.buf.ru8()
                    chunk["data"]["unit"] = {
                        "raw": unit,
                        "name": {
                            1: "Meters"
                        }.get(unit, "Unknown")
                    }
                case "iCCP":
                    chunk["data"]["profile-name"] = self.buf.rzs()

                    compression_method = self.buf.ru8()
                    match compression_method:
                        case 0:
                            chunk["data"]["compression-method"] = {
                                "raw": 0,
                                "name": "DEFLATE"
                            }
                            chunk["data"]["profile"] = chew(
                                b"ICC_PROFILE\x00\x00\x00" +
                                zlib.decompress(self.buf.readunit()))
                        case _:
                            chunk["data"]["compression-method"] = {
                                "raw": compression_method,
                                "name": "Unknown"
                            }
                case "iTXt":
                    chunk["data"]["keyword"] = self.buf.rzs()

                    compressed = bool(self.buf.ru8())
                    chunk["data"]["compressed"] = compressed
                    compression_method = self.buf.ru8()
                    chunk["data"]["language-tag"] = self.buf.rzs()
                    chunk["data"]["translated-keyword"] = self.buf.rzs()

                    match compression_method:
                        case 0:
                            if compressed:
                                chunk["data"]["compression-method"] = {
                                    "raw": 0,
                                    "name": "DEFLATE"
                                }
                                chunk["data"]["text"] = zlib.decompress(
                                    self.buf.readunit())
                            else:
                                chunk["data"]["compression-method"] = {
                                    "raw": 0,
                                    "name": "Uncompressed"
                                }
                                chunk["data"]["text"] = self.buf.readunit()
                        case _:
                            chunk["data"]["compression-method"] = {
                                "raw": compression_method,
                                "name": "Unknown"
                            }

                    try:
                        chunk["data"]["text"] = chunk["data"]["text"].decode(
                            "utf-8")
                    except UnicodeDecodeError:
                        try:
                            chunk["data"]["text"] = chunk["data"][
                                "text"].decode("utf-16")
                        except UnicodeDecodeError:
                            chunk["data"]["text"] = chunk["data"][
                                "text"].decode("latin-1")

                    if chunk["data"]["keyword"] == "XML:com.adobe.xmp":
                        chunk["data"]["text"] = utils.xml_to_dict(
                            chunk["data"]["text"])
                case "cHRM":
                    chunk["data"]["white"] = [
                        self.buf.ru32() / 100000 for _ in range(0, 2)
                    ]
                    chunk["data"]["red"] = [
                        self.buf.ru32() / 100000 for _ in range(0, 2)
                    ]
                    chunk["data"]["green"] = [
                        self.buf.ru32() / 100000 for _ in range(0, 2)
                    ]
                    chunk["data"]["blue"] = [
                        self.buf.ru32() / 100000 for _ in range(0, 2)
                    ]
                case "tEXt":
                    chunk["data"]["keyword"] = self.buf.rzs()
                    chunk["data"]["text"] = self.buf.readunit().decode(
                        "latin-1")
                case "bKGD":
                    match self.buf.unit:
                        case 1:
                            chunk["data"]["index"] = self.buf.ru8()
                        case 2:
                            chunk["data"]["gray"] = self.buf.ru16()
                        case 6:
                            chunk["data"]["red"] = self.buf.ru16()
                            chunk["data"]["green"] = self.buf.ru16()
                            chunk["data"]["blue"] = self.buf.ru16()
                case "tIME":
                    chunk["data"]["date"] = datetime.datetime(
                        self.buf.ru16(),
                        self.buf.ru8(),
                        self.buf.ru8(),
                        self.buf.ru8(),
                        self.buf.ru8(),
                        self.buf.ru8(),
                        tzinfo=datetime.timezone.utc).isoformat()
                case "gAMA":
                    chunk["data"]["gamma"] = self.buf.ru32() / 100000
                case "IDAT" | "IEND" | "PLTE" | "tRNS" | "npOl" | "npTc":
                    pass
                case _:
                    chunk["data"]["unknown"] = True

            meta["chunks"].append(chunk)

            self.buf.skipunit()
            self.buf.skip(4)
            self.buf.popunit()

        return meta


@module.register
class TIFFModule(module.RuminantModule):
    TAG_IDS = {
        0: "GPSVersionID",
        1: "GPSLatitudeRef",
        2: "GPSLatitude",
        3: "GPSLongitudeRef",
        4: "GPSLongitude",
        5: "GPSAltitudeRef",
        6: "GPSAltitude",
        7: "GPSTimeStamp",
        8: "GPSSatellites",
        9: "GPSStatus",
        10: "GPSMeasureMode",
        11: "GPSDOP",
        12: "GPSSpeedRef",
        13: "GPSSpeed",
        14: "GPSTrackRef",
        15: "GPSTrack",
        16: "GPSImgDirectionRef",
        17: "GPSImgDirection",
        18: "GPSMapDatum",
        19: "GPSDestLatitudeRef",
        20: "GPSDestLatitude",
        21: "GPSDestLongitudeRef",
        22: "GPSDestLongitude",
        23: "GPSDestBearingRef",
        24: "GPSDestBearing",
        25: "GPSDestDistanceRef",
        26: "GPSDestDistance",
        27: "GPSProcessingMethod",
        28: "GPSAreaInformation",
        29: "GPSDateStamp",
        30: "GPSDifferential",
        31: "GPSHPositioningError",
        254: "NewSubfileType",
        255: "SubfileType",
        256: "ImageWidth",
        257: "ImageLength",
        258: "BitsPerSample",
        259: "Compression",
        262: "PhotometricInterpretation",
        263: "Threshholding",
        264: "CellWidth",
        265: "CellLength",
        266: "FillOrder",
        269: "DocumentName",
        270: "ImageDescription",
        271: "Make",
        272: "Model",
        273: "StripOffsets",
        274: "Orientation",
        277: "SamplesPerPixel",
        278: "RowsPerStrip",
        279: "StripByteCounts",
        280: "MinSampleValue",
        281: "MaxSampleValue",
        282: "XResolution",
        283: "XResolution",
        284: "PlanarConfiguration",
        285: "PageName",
        286: "XPosition",
        287: "YPosition",
        288: "FreeOffsets",
        289: "FreeByteCounts",
        290: "GrayResponseUnit",
        291: "GrayResponseCurve",
        292: "T4Options",
        293: "T6Options",
        296: "ResolutionUnit",
        297: "PageNumber",
        301: "TransferFunction",
        305: "Software",
        306: "DateTime",
        315: "Artist",
        316: "HostComputer",
        317: "Predictor",
        318: "WhitePoint",
        319: "PrimaryChromaticities",
        320: "ColorMap",
        321: "HalftoneHints",
        322: "TileWidth",
        323: "TileLength",
        324: "TileOffset",
        325: "TileByteCounts",
        332: "InkSet",
        333: "InkNames",
        334: "NumberOfInks",
        336: "DotRange",
        337: "TargetPrinter",
        338: "ExtraSamples",
        339: "SampleFormat",
        340: "SMinSampleValue",
        341: "SMaxSampleValue",
        342: "TransferRange",
        512: "JPEGProc",
        513: "JPEGInterchangeFormat",
        514: "JPEGInterchangeFormatLngth",
        515: "JPEGRestartInterval",
        517: "JPEGLosslessPredictors",
        518: "JPEGPointTransforms",
        519: "JPEGQTables",
        520: "JPEGDCTables",
        521: "JPEGACTables",
        529: "YCbCrCoefficients",
        530: "YCbCrSubSampling",
        531: "YCbCrPositioning",
        532: "ReferenceBlackWhite",
        33432: "Copyright",
        33434: "ExposureTime",
        33437: "FNumber",
        34665: "ExifIFDPointer",
        34850: "ExposureProgram",
        34852: "SpectralSensitivity",
        34853: "GPSInfoIFDPointer",
        34855: "PhotographicSensitivity",
        34856: "OECF",
        34864: "SensitivityType",
        34865: "StandardOutputSensitivity",
        34866: "RecommendedExposureIndex",
        34867: "ISOSpeed",
        34868: "ISOSpeedLatitudeyyy",
        34869: "ISOSpeedLatitudezzz",
        36864: "ExifVersion",
        36867: "DateTimeOriginal",
        36868: "DateTimeDigitized",
        36880: "OffsetTime",
        36881: "OffsetTimeOriginal",
        36882: "OffsetTimeDigitized",
        37121: "ComponentsConfiguration",
        37122: "CompressedBitsPerPixel",
        37377: "ShutterSpeedValue",
        37378: "ApertureValue",
        37379: "BrightnessValue",
        37380: "ExposureBiasValue",
        37381: "MaxApertureValue",
        37382: "SubjectDistance",
        37383: "MeteringMode",
        37384: "LightSource",
        37385: "Flash",
        37386: "FocalLength",
        37396: "SubjectArea",
        37500: "MakerNote",
        37510: "UserComment",
        37520: "SubSecTime",
        37521: "SubSecTimeOriginal",
        37522: "SubSecTimeDigitized",
        40960: "FlashpixVersion",
        40961: "ColorSpace",
        40962: "PixelXDimension",
        40963: "PixelYDimension",
        40964: "RelatedSoundFile",
        40965: "InteroperabilityIFDPointer",
        41483: "FlashEnergy",
        41484: "SpatialFrequencyResponse",
        41486: "FocalPlaneXResolution",
        41487: "FocalPlaneYResolution",
        41488: "FocalPlaneResolutionUnit",
        41492: "SubjectLocation",
        41493: "ExposureIndex",
        41495: "SensingMethod",
        41728: "FileSource",
        41729: "SceneType",
        41730: "CFAPattern",
        41985: "CustomRendered",
        41986: "ExposureMode",
        41987: "WhiteBalance",
        41988: "DigitalZoomRatio",
        41989: "FocalLengthIn35mmFilm",
        41990: "SceneCaptureType",
        41991: "GainControl",
        41992: "Contrast",
        41993: "Saturation",
        41994: "Sharpness",
        41995: "DeviceSettingDescription",
        41996: "SubjectDistanceRange",
        42016: "ImageUniqueID",
        42032: "CameraOwnerName",
        42033: "BodySerialNumber",
        42034: "LensSpecification",
        42035: "LensMake",
        42036: "LensModel",
        42037: "LensSerialNumber",
        42080: "CompositeImage",
        42240: "Gamma",
        59932: "Padding",
    }

    FIELD_TYPES = {
        1: "Byte",
        2: "ASCII string",
        3: "Short",
        4: "Long",
        5: "Rational",
        6: "Signed byte",
        7: "Undefined",
        8: "Signed short",
        9: "Signed long",
        10: "Signed rational",
        11: "Float",
        12: "Double",
    }

    def identify(buf):
        return buf.peek(4) in (b"II*\x00", b"MM\x00*")

    def chew(self):
        meta = {}
        meta["type"] = "tiff"

        header = self.buf.read(4)
        le = header[0] == 0x49

        meta["endian"] = "little" if le else "big"

        meta["data"] = {}
        meta["data"]["tags"] = []

        offset_queue = []
        thumbnail_offset = None
        thumbnail_length = None
        thumbnail_tag = None
        while True:
            offset = self.buf.ru32l() if le else self.buf.ru32()

            if offset == 0:
                if len(offset_queue):
                    offset = offset_queue.pop()
                else:
                    break

            self.buf.seek(offset)

            entry_count = self.buf.ru16l() if le else self.buf.ru16()
            for i in range(0, entry_count):
                tag = {}

                tag_id = self.buf.ru16l() if le else self.buf.ru16()
                tag["id"] = (self.TAG_IDS.get(tag_id, "Unknown") +
                             f" (0x{hex(tag_id)[2:].zfill(4)})")
                field_type = self.buf.ru16l() if le else self.buf.ru16()
                tag["type"] = (self.FIELD_TYPES.get(field_type, "Unknown") +
                               f" (0x{hex(field_type)[2:].zfill(4)})")
                count = self.buf.ru32l() if le else self.buf.ru32()
                tag["count"] = count
                offset_field_offset = self.buf.tell()
                tag_offset = self.buf.ru32l() if le else self.buf.ru32()
                tag["offset-or-value"] = tag_offset

                tag["values"] = []
                with self.buf:
                    if ((field_type in (1, 2) and count <= 4)
                            or (field_type in (3, 8, 11) and count <= 2)
                            or (field_type in (4, 9, 12) and count <= 1)):
                        self.buf.seek(offset_field_offset)
                    else:
                        self.buf.seek(tag_offset)

                    for i in range(0, count):
                        match field_type:
                            case 1:
                                tag["values"].append(
                                    self.buf.ru8l() if le else self.buf.ru8())
                            case 2:
                                string = b""
                                while self.buf.peek(1)[0]:
                                    string += self.buf.read(1)

                                self.buf.skip(1)
                                tag["values"].append(string.decode("latin-1"))
                                count -= len(string) + 1
                                if count <= 0:
                                    break
                            case 3:
                                tag["values"].append(self.buf.ru16l(
                                ) if le else self.buf.ru16())
                            case 4:
                                value = (self.buf.ru32l()
                                         if le else self.buf.ru32())
                                tag["values"].append(value)

                                if "IFD" in tag["id"]:
                                    offset_queue.append(value)
                            case 5:
                                value = {}
                                value["numerator"] = (self.buf.ru32l() if le
                                                      else self.buf.ru32())
                                value["denominator"] = (self.buf.ru32l() if le
                                                        else self.buf.ru32())
                                value["rational_approx"] = (
                                    value["numerator"] / value["denominator"]
                                    if value["denominator"] else "NaN")
                                tag["values"].append(value)
                            case 6:
                                tag["values"].append(
                                    self.buf.ri8l() if le else self.buf.ri8())
                            case 8:
                                tag["values"].append(self.buf.ri16l(
                                ) if le else self.buf.ri16())
                            case 9:
                                tag["values"].append(self.buf.ri32l(
                                ) if le else self.buf.ri32())
                            case 10:
                                value = {}
                                value["numerator"] = (self.buf.ri32l() if le
                                                      else self.buf.ri32())
                                value["denominator"] = (self.buf.ri32l() if le
                                                        else self.buf.ri32())
                                value["rational_approx"] = (
                                    value["numerator"] / value["denominator"]
                                    if value["denominator"] else "NaN")
                                tag["values"].append(value)
                            case 11:
                                tag["values"].append(self.buf.rf32l(
                                ) if le else self.buf.rf32())
                            case 12:
                                tag["values"].append(self.buf.rf64l(
                                ) if le else self.buf.rf64())
                            case _:
                                tag["unknown"] = True

                match tag_id:
                    case 513:
                        thumbnail_offset = tag["values"][0]
                        thumbnail_tag = tag
                    case 514:
                        thumbnail_length = tag["values"][0]

                if (thumbnail_tag is not None and thumbnail_offset is not None
                        and thumbnail_length is not None):
                    with self.buf:
                        self.buf.seek(thumbnail_offset)

                        with self.buf.sub(thumbnail_length):
                            thumbnail_tag["parsed"] = chew(self.buf)

                    thumbnail_tag = None
                    thumbnail_offset = None
                    thumbnail_length = None

                meta["data"]["tags"].append(tag)

        self.buf.skip(self.buf.available())

        return meta


@module.register
class GifModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(3) == b"GIF"

    def chew(self):
        meta = {}
        meta["type"] = "gif"

        self.buf.skip(3)

        meta["version"] = self.buf.rs(3)

        meta["header"] = {}
        meta["header"]["width"] = self.buf.ru16l()
        meta["header"]["height"] = self.buf.ru16l()

        gct = self.buf.ru8()
        meta["header"]["gct-size"] = 2**((gct >> 5) + 1) * 3
        meta["header"]["is-sorted"] = bool((gct >> 4) & 1)
        meta["header"]["color-resolution"] = (gct >> 1) & 0x07
        meta["header"]["gct-present"] = bool(gct & 1)
        meta["header"]["background-color-index"] = self.buf.ru8()
        meta["header"]["pixel-aspect-ratio"] = self.buf.ru8()

        if meta["header"]["gct-present"]:
            self.buf.skip(meta["header"]["gct-size"])

        meta["blocks"] = []
        running = True
        while running:
            block = {}
            block["offset"] = self.buf.tell()

            typ = self.buf.ru8()
            match typ:
                case 0x2c:
                    block["type"] = "image-descriptor"
                    block["data"] = {}
                    block["data"]["left"] = self.buf.ru16()
                    block["data"]["top"] = self.buf.ru16()
                    block["data"]["width"] = self.buf.ru16()
                    block["data"]["height"] = self.buf.ru16()

                    lct = self.buf.ru8()
                    block["data"]["lct-present"] = bool(lct & 0x80)
                    block["data"]["is-interlaced"] = bool(lct & 0x40)
                    block["data"]["is-sorted"] = bool(lct & 0x20)
                    block["data"]["reserved"] = (lct >> 3) & 0x03
                    block["data"]["lct-size"] = 2**((lct & 0x07) + 1) * 3

                    if block["data"]["lct-present"]:
                        self.buf.skip(block["data"]["lct-size"])

                    block["data"]["lzw-minimum-code-size"] = self.buf.ru8()
                    block["subdata-length"] = len(self.read_subblocks())
                case 0x21:
                    block["type"] = "extension"
                    label = self.buf.ru8()
                    block["label"] = label
                    block["size"] = self.buf.ru8()

                    processed_subdata = False
                    match label:
                        case 0xf9:
                            block["extension"] = "gce"

                            flags = self.buf.ru8()
                            block["data"] = {
                                "reserved": flags >> 5,
                                "disposal-method": (flags >> 2) & 0x07,
                                "user-input-flag": bool(flags & 0x02),
                                "transparent-color-flag": bool(flags & 0x01),
                                "delay-time": self.buf.ru16(),
                                "transparent-color-index": self.buf.ru8()
                            }
                        case 0xfe:
                            block["extension"] = "comment"
                            block["data"] = self.read_subblocks().decode(
                                "utf-8")
                            processed_subdata = True
                        case 0xff:
                            block["extension"] = "application"
                            block["application"] = self.buf.rs(block["size"])

                            match block["application"]:
                                case "NETSCAPE2.0":
                                    data = self.read_subblocks()
                                    block["data"] = {
                                        "id": data[0],
                                        "loop":
                                        int.from_bytes(data[1:], "big")
                                    }

                                    processed_subdata = True
                                case _:
                                    block["unknown"] = True
                        case _:
                            block["data"] = self.buf.rh(block["size"])
                            block["unknown"] = True

                    if not processed_subdata:
                        if self.buf.peek(1)[0]:
                            block["subdata"] = self.read_subblocks().hex()
                        else:
                            self.buf.skip(1)
                case 0x3b:
                    block["type"] = "end"
                    running = False
                case _:
                    raise ValueError(f"Unknown GIF block type {typ}")

            meta["blocks"].append(block)

        return meta

    def read_subblocks(self):
        data = b""

        while True:
            length = self.buf.ru8()
            if length == 0:
                return data

            data += self.buf.read(length)
