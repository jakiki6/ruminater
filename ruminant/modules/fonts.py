from .. import module, utils


@module.register
class TrueTypeModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(5) in (b"\x00\x01\x00\x00\x00", b"OTTO\x00")

    def chew(self):
        meta = {}
        meta["type"] = "truetype"

        self.buf.skip(4)

        num_tables = self.buf.ru16()
        meta["table-count"] = num_tables
        meta["search-range"] = self.buf.ru16()
        meta["entry-selector"] = self.buf.ru16()
        meta["range-shift"] = self.buf.ru16()

        meta["tables"] = []
        for i in range(0, num_tables):
            table = {}

            table["tag"] = self.buf.rs(4, "latin-1")
            table["checksum"] = self.buf.rh(4)
            table["offset"] = self.buf.ru32()
            table["length"] = self.buf.ru32()

            with self.buf:
                self.buf.seek(table["offset"])
                self.buf.setunit(table["length"])

                table["data"] = {}
                match table["tag"]:
                    case "OS/2":
                        table["data"]["version"] = self.buf.ru16()
                        table["data"]["x-avg-char-width"] = self.buf.ri16()
                        table["data"]["us-weight-class"] = self.buf.ru16()
                        table["data"]["us-width-class"] = self.buf.ru16()
                        table["data"]["fs-type"] = self.buf.ri16()
                        table["data"]["y-subscript-x-size"] = self.buf.ri16()
                        table["data"]["y-subscript-y-size"] = self.buf.ri16()
                        table["data"]["y-subscript-x-offset"] = self.buf.ri16()
                        table["data"]["y-subscript-y-offset"] = self.buf.ri16()
                        table["data"]["y-superscript-x-size"] = self.buf.ri16()
                        table["data"]["y-superscript-y-size"] = self.buf.ri16()
                        table["data"][
                            "y-superscript-x-offset"] = self.buf.ri16()
                        table["data"][
                            "y-superscript-y-offset"] = self.buf.ri16()
                        table["data"]["y-strikeout-size"] = self.buf.ri16()
                        table["data"]["y-strikeout-position"] = self.buf.ri16()
                        table["data"]["s-family-class"] = self.buf.ri16()
                        table["data"]["panose"] = self.buf.rh(10)
                        table["data"]["ul-unicode-range"] = self.buf.rh(16)
                        table["data"]["ach-vend-id"] = self.buf.rs(4)
                        table["data"]["fs-selection"] = self.buf.ru16()
                        table["data"]["fs-first-char-index"] = self.buf.ru16()
                        table["data"]["fs-last-char-index"] = self.buf.ru16()

                        if self.buf.unit >= 2:
                            table["data"]["s-typo-descender"] = self.buf.ri16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["s-typo-line-gap"] = self.buf.ri16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["us-win-ascent"] = self.buf.ru16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["us-win-descent"] = self.buf.ru16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 4:
                            table["data"][
                                "ul-code-page-range1"] = self.buf.ru32()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 4:
                            table["data"][
                                "ul-code-page-range2"] = self.buf.ru32()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["sx-height"] = self.buf.ri16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["s-cap-height"] = self.buf.ri16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["us-default-char"] = self.buf.ru16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["us-break-char"] = self.buf.ru16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"]["us-max-context"] = self.buf.ru16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"][
                                "us-lower-point-size"] = self.buf.ru16()
                        else:
                            self.buf.skipunit()
                        if self.buf.unit >= 2:
                            table["data"][
                                "us-upper-point-size"] = self.buf.ru16()
                        else:
                            self.buf.skipunit()
                    case "cvt ":
                        table["data"]["entry-count"] = self.buf.unit // 4
                    case "fpgm" | "prep":
                        table["data"]["instruction-count"] = self.buf.unit
                    case "head":
                        table["data"]["version"] = str(
                            self.buf.ru16()) + "." + str(self.buf.ru16())
                        table["data"]["revision"] = self.buf.ru32()
                        table["data"]["checksum-adjustment"] = self.buf.ru32()
                        table["data"]["magic"] = self.buf.rh(4)
                        table["data"]["flags"] = self.buf.rh(2)
                        table["data"]["units-per-em"] = self.buf.ru16()
                        table["data"]["created"] = utils.mp4_time_to_iso(
                            self.buf.ri64())
                        table["data"]["modified"] = utils.mp4_time_to_iso(
                            self.buf.ri64())
                        table["data"]["x-min"] = self.buf.ri16()
                        table["data"]["y-min"] = self.buf.ri16()
                        table["data"]["x-max"] = self.buf.ri16()
                        table["data"]["y-max"] = self.buf.ri16()

                        mac_style = self.buf.ru16()
                        table["data"]["mac-style"] = {
                            "raw": mac_style,
                            "bold": bool(mac_style & 0x01),
                            "italic": bool(mac_style & 0x02),
                            "underline": bool(mac_style & 0x04),
                            "outline": bool(mac_style & 0x08),
                            "shadow": bool(mac_style & 0x10),
                            "condensed": bool(mac_style & 0x20),
                            "extended": bool(mac_style & 0x40)
                        }

                        table["data"]["lowest-rec-ppem"] = self.buf.ru16()
                        table["data"]["font-direction-hint"] = self.buf.ri16()
                        table["data"]["index-to-loc-format"] = self.buf.ri16()
                        table["data"]["glyph-data-format"] = self.buf.ri16()
                    case "hhea":
                        table["data"]["version"] = str(
                            self.buf.ru16()) + "." + str(self.buf.ru16())
                        table["data"]["ascent"] = self.buf.ri16()
                        table["data"]["descent"] = self.buf.ri16()
                        table["data"]["line-gap"] = self.buf.ri16()
                        table["data"]["advance-width-max"] = self.buf.ru16()
                        table["data"]["min-left-side-bearing"] = self.buf.ri16(
                        )
                        table["data"][
                            "min-right-side-bearing"] = self.buf.ri16()
                        table["data"]["x-max-extent"] = self.buf.ri16()
                        table["data"]["caret-slope-rise"] = self.buf.ri16()
                        table["data"]["caret-slope-run"] = self.buf.ri16()
                        table["data"]["caret-offset"] = self.buf.ri16()
                        table["data"]["reserved"] = self.buf.ri16()
                        table["data"]["reserved"] = self.buf.ri16()
                        table["data"]["reserved"] = self.buf.ri16()
                        table["data"]["reserved"] = self.buf.ri16()
                        table["data"]["metric-data-format"] = self.buf.ri16()
                        table["data"][
                            "num-of-long-hor-metrics"] = self.buf.ru16()
                    case "maxp":
                        table["data"]["version"] = str(
                            self.buf.ru16()) + "." + str(self.buf.ru16())
                        table["data"]["num-glyphs"] = self.buf.ru16()
                        if table["data"]["version"] != "0.5":
                            table["data"]["max-points"] = self.buf.ru16()
                            table["data"]["max-contours"] = self.buf.ru16()
                            table["data"][
                                "max-component-points"] = self.buf.ru16()
                            table["data"][
                                "max-component-contours"] = self.buf.ru16()
                            table["data"]["max-zones"] = self.buf.ru16()
                            table["data"][
                                "max-twilight-points"] = self.buf.ru16()
                            table["data"]["max-storage"] = self.buf.ru16()
                            table["data"]["max-function-defs"] = self.buf.ru16(
                            )
                            table["data"][
                                "max-instruction-defs"] = self.buf.ru16()
                            table["data"][
                                "max-stack-elements"] = self.buf.ru16()
                            table["data"][
                                "max-size-of-instructions"] = self.buf.ru16()
                            table["data"][
                                "max-component-elements"] = self.buf.ru16()
                            table["data"][
                                "max-component-depth"] = self.buf.ru16()
                    case "name":
                        offset = self.buf.tell()
                        table["data"]["format"] = self.buf.ru16()
                        count = self.buf.ru16()
                        table["data"]["count"] = count
                        string_offset = self.buf.ru16()
                        table["data"]["string-offset"] = string_offset

                        table["data"]["entries"] = []
                        for i in range(0, count):
                            entry = {}
                            platform_id = self.buf.ru16()
                            entry["platform"] = {
                                0: "Unicode",
                                1: "Macintosh",
                                2: "Reserved",
                                3: "Microsoft"
                            }.get(platform_id, "Unknown"
                                  ) + f" (0x{hex(platform_id)[2:].zfill(4)})"

                            platform_specific_id = self.buf.ru16()
                            entry["platform-specific"] = {
                                0: {
                                    0:
                                    "Version 1.0 semantics",
                                    1:
                                    "Version 1.1 semantics",
                                    2:
                                    "ISO 10646 1993 semantics (deprecated)",
                                    3:
                                    "Unicode 2.0 or later semantics (BMP only)",
                                    4:
                                    "Unicode 2.0 or later semantics (non-BMP characters allowed)"  # noqa: E501
                                },
                                1: {
                                    0: "Roman",
                                    1: "Japanese",
                                    2: "Traditional Chinese",
                                    3: "Korean",
                                    4: "Arabic",
                                    5: "Hebrew",
                                    6: "Greek",
                                    7: "Russian",
                                    8: "RSymbol",
                                    9: "Devanagari",
                                    10: "Gurmukhi",
                                    11: "Gujarati",
                                    12: "Oriya",
                                    13: "Bengali",
                                    14: "Tamil",
                                    15: "Telugu",
                                    16: "Kannada",
                                    17: "Malayalam",
                                    18: "Sinhalese",
                                    19: "Burmese",
                                    20: "Khmer",
                                    21: "Thai",
                                    22: "Laotian",
                                    23: "Georgian",
                                    24: "Armenian",
                                    25: "Simplified Chinese",
                                    26: "Tibetan",
                                    27: "Mongolian",
                                    28: "Geez",
                                    29: "Slavic",
                                    30: "Vietnamese",
                                    31: "Sindhi",
                                    32: "(Uninterpreted)"
                                },
                                3: {
                                    0: "Symbol",
                                    1: "Unicode BMP",
                                    2: "ShiftJIS",
                                    3: "PRC",
                                    4: "Big5",
                                    5: "Wansung",
                                    6: "Johab",
                                    7: "Reserved",
                                    8: "Reserved",
                                    9: "Reserved",
                                    10: "Unicode full repertoire"
                                }
                            }.get(platform_id, {}).get(
                                platform_specific_id, "Unknown"
                            ) + f" (0x{hex(platform_specific_id)[2:].zfill(4)})"

                            language_id = self.buf.ru16()
                            entry["language"] = {
                                1: {
                                    0: "English",
                                    1: "French",
                                    2: "German",
                                    3: "Italian",
                                    4: "Dutch",
                                    5: "Swedish",
                                    6: "Spanish",
                                    7: "Danish",
                                    8: "Portuguese",
                                    9: "Norwegian",
                                    10: "Hebrew",
                                    11: "Japanese",
                                    12: "Arabic",
                                    13: "Finnish",
                                    14: "Greek",
                                    15: "Icelandic",
                                    16: "Maltese",
                                    17: "Turkish",
                                    18: "Croatian",
                                    19: "Chinese (traditional)",
                                    20: "Urdu",
                                    21: "Hindi",
                                    22: "Thai",
                                    23: "Korean",
                                    24: "Lithuanian",
                                    25: "Polish",
                                    26: "Hungarian",
                                    27: "Estonian",
                                    28: "Latvian",
                                    29: "Sami",
                                    30: "Faroese",
                                    31: "Farsi/Persian",
                                    32: "Russian",
                                    33: "Chinese (simplified)",
                                    34: "Flemish",
                                    35: "Irish Gaelic",
                                    36: "Albanian",
                                    37: "Romanian",
                                    38: "Czech",
                                    39: "Slovak",
                                    40: "Slovenian",
                                    41: "Yiddish",
                                    42: "Serbian",
                                    43: "Macedonian",
                                    44: "Bulgarian",
                                    45: "Ukrainian",
                                    46: "Byelorussian",
                                    47: "Uzbek",
                                    48: "Kazakh",
                                    49: "Azerbaijani (Cyrillic script)",
                                    50: "Azerbaijani (Arabic script)",
                                    51: "Armenian",
                                    52: "Georgian",
                                    53: "Moldavian",
                                    54: "Kirghiz",
                                    55: "Tajiki",
                                    56: "Turkmen",
                                    57: "Mongolian (Mongolian script)",
                                    58: "Mongolian (Cyrillic script)",
                                    59: "Pashto",
                                    60: "Kurdish",
                                    61: "Kashmiri",
                                    62: "Sindhi",
                                    63: "Tibetan",
                                    64: "Nepali",
                                    65: "Sanskrit",
                                    66: "Marathi",
                                    67: "Bengali",
                                    68: "Assamese",
                                    69: "Gujarati",
                                    70: "Punjabi",
                                    71: "Oriya",
                                    72: "Malayalam",
                                    73: "Kannada",
                                    74: "Tamil",
                                    75: "Telugu",
                                    76: "Sinhalese",
                                    77: "Burmese",
                                    78: "Khmer",
                                    79: "Lao",
                                    80: "Vietnamese",
                                    81: "Indonesian",
                                    82: "Tagalog",
                                    83: "Malay (Roman script)",
                                    84: "Malay (Arabic script)",
                                    85: "Amharic",
                                    86: "Tigrinya",
                                    87: "Galla",
                                    88: "Somali",
                                    89: "Swahili",
                                    90: "Kinyarwanda/Ruanda",
                                    91: "Rundi",
                                    92: "Nyanja/Chewa",
                                    93: "Malagasy",
                                    94: "Esperanto",
                                    128: "Welsh",
                                    129: "Basque",
                                    130: "Catalan",
                                    131: "Latin",
                                    132: "Quechua",
                                    133: "Guarani",
                                    134: "Aymara",
                                    135: "Tatar",
                                    136: "Uighur",
                                    137: "Dzongkha",
                                    138: "Javanese (Roman script)",
                                    139: "Sundanese (Roman script)",
                                    140: "Galician",
                                    141: "Afrikaans",
                                    142: "Breton",
                                    143: "Inuktitut",
                                    144: "Scottish Gaelic",
                                    145: "Manx Gaelic",
                                    146: "Irish Gaelic (with dot above)",
                                    147: "Tongan",
                                    148: "Greek (polytonic)",
                                    149: "Greenlandic",
                                    150: "Azerbaijani (Roman script)"
                                },
                                3: {
                                    1: "ar",
                                    2: "bg",
                                    3: "ca",
                                    4: "zh-Hans",
                                    5: "cs",
                                    6: "da",
                                    7: "de",
                                    8: "el",
                                    9: "en",
                                    10: "es",
                                    11: "fi",
                                    12: "fr",
                                    13: "he",
                                    14: "hu",
                                    15: "is",
                                    16: "it",
                                    17: "ja",
                                    18: "ko",
                                    19: "nl",
                                    20: "no",
                                    21: "pl",
                                    22: "pt",
                                    23: "rm",
                                    24: "ro",
                                    25: "ru",
                                    26: "hr",
                                    27: "sk",
                                    28: "sq",
                                    29: "sv",
                                    30: "th",
                                    31: "tr",
                                    32: "ur",
                                    33: "id",
                                    34: "uk",
                                    35: "be",
                                    36: "sl",
                                    37: "et",
                                    38: "lv",
                                    39: "lt",
                                    40: "tg",
                                    41: "fa",
                                    42: "vi",
                                    43: "hy",
                                    44: "az",
                                    45: "eu",
                                    46: "hsb",
                                    47: "mk",
                                    48: "st",
                                    49: "ts",
                                    50: "tn",
                                    51: "ve",
                                    52: "xh",
                                    53: "zu",
                                    54: "af",
                                    55: "ka",
                                    56: "fo",
                                    57: "hi",
                                    58: "mt",
                                    59: "se",
                                    60: "ga",
                                    61: "yi",
                                    62: "ms",
                                    63: "kk",
                                    64: "ky",
                                    65: "sw",
                                    66: "tk",
                                    67: "uz",
                                    68: "tt",
                                    69: "bn",
                                    70: "pa",
                                    71: "gu",
                                    72: "or",
                                    73: "ta",
                                    74: "te",
                                    75: "kn",
                                    76: "ml",
                                    77: "as",
                                    78: "mr",
                                    79: "sa",
                                    80: "mn",
                                    81: "bo",
                                    82: "cy",
                                    83: "km",
                                    84: "lo",
                                    85: "my",
                                    86: "gl",
                                    87: "kok",
                                    88: "mni",
                                    89: "sd",
                                    90: "syr",
                                    91: "si",
                                    92: "chr",
                                    93: "iu",
                                    94: "am",
                                    95: "tzm",
                                    96: "ks",
                                    97: "ne",
                                    98: "fy",
                                    99: "ps",
                                    100: "fil",
                                    101: "dv",
                                    102: "bin",
                                    103: "ff",
                                    104: "ha",
                                    105: "ibb",
                                    106: "yo",
                                    107: "quz",
                                    108: "nso",
                                    109: "ba",
                                    110: "lb",
                                    111: "kl",
                                    112: "ig",
                                    113: "kr",
                                    114: "om",
                                    115: "ti",
                                    116: "gn",
                                    117: "haw",
                                    118: "la",
                                    119: "so",
                                    120: "ii",
                                    121: "pap",
                                    122: "arn",
                                    123: "Neither",
                                    124: "moh",
                                    125: "Neither",
                                    126: "br",
                                    127: "Reserved",
                                    128: "ug",
                                    129: "mi",
                                    130: "oc",
                                    131: "co",
                                    132: "gsw",
                                    133: "sah",
                                    134: "qut",
                                    135: "rw",
                                    136: "wo",
                                    137: "Neither",
                                    138: "Neither",
                                    139: "Neither",
                                    140: "prs",
                                    141: "Neither",
                                    142: "Neither",
                                    143: "Neither",
                                    144: "Neither",
                                    145: "gd",
                                    146: "ku",
                                    147: "quc",
                                    1025: "ar-SA",
                                    1026: "bg-BG",
                                    1027: "ca-ES",
                                    1028: "zh-TW",
                                    1029: "cs-CZ",
                                    1030: "da-DK",
                                    1031: "de-DE",
                                    1032: "el-GR",
                                    1033: "en-US",
                                    1034: "es-ES_tradnl",
                                    1035: "fi-FI",
                                    1036: "fr-FR",
                                    1037: "he-IL",
                                    1038: "hu-HU",
                                    1039: "is-IS",
                                    1040: "it-IT",
                                    1041: "ja-JP",
                                    1042: "ko-KR",
                                    1043: "nl-NL",
                                    1044: "nb-NO",
                                    1045: "pl-PL",
                                    1046: "pt-BR",
                                    1047: "rm-CH",
                                    1048: "ro-RO",
                                    1049: "ru-RU",
                                    1050: "hr-HR",
                                    1051: "sk-SK",
                                    1052: "sq-AL",
                                    1053: "sv-SE",
                                    1054: "th-TH",
                                    1055: "tr-TR",
                                    1056: "ur-PK",
                                    1057: "id-ID",
                                    1058: "uk-UA",
                                    1059: "be-BY",
                                    1060: "sl-SI",
                                    1061: "et-EE",
                                    1062: "lv-LV",
                                    1063: "lt-LT",
                                    1064: "tg-Cyrl-TJ",
                                    1065: "fa-IR",
                                    1066: "vi-VN",
                                    1067: "hy-AM",
                                    1068: "az-Latn-AZ",
                                    1069: "eu-ES",
                                    1070: "hsb-DE",
                                    1071: "mk-MK",
                                    1072: "st-ZA",
                                    1073: "ts-ZA",
                                    1074: "tn-ZA",
                                    1075: "ve-ZA",
                                    1076: "xh-ZA",
                                    1077: "zu-ZA",
                                    1078: "af-ZA",
                                    1079: "ka-GE",
                                    1080: "fo-FO",
                                    1081: "hi-IN",
                                    1082: "mt-MT",
                                    1083: "se-NO",
                                    1085: "yi-001",
                                    1086: "ms-MY",
                                    1087: "kk-KZ",
                                    1088: "ky-KG",
                                    1089: "sw-KE",
                                    1090: "tk-TM",
                                    1091: "uz-Latn-UZ",
                                    1092: "tt-RU",
                                    1093: "bn-IN",
                                    1094: "pa-IN",
                                    1095: "gu-IN",
                                    1096: "or-IN",
                                    1097: "ta-IN",
                                    1098: "te-IN",
                                    1099: "kn-IN",
                                    1100: "ml-IN",
                                    1101: "as-IN",
                                    1102: "mr-IN",
                                    1103: "sa-IN",
                                    1104: "mn-MN",
                                    1105: "bo-CN",
                                    1106: "cy-GB",
                                    1107: "km-KH",
                                    1108: "lo-LA",
                                    1109: "my-MM",
                                    1110: "gl-ES",
                                    1111: "kok-IN",
                                    1112: "mni-IN",
                                    1113: "sd-Deva-IN",
                                    1114: "syr-SY",
                                    1115: "si-LK",
                                    1116: "chr-Cher-US",
                                    1117: "iu-Cans-CA",
                                    1118: "am-ET",
                                    1119: "tzm-Arab-MA",
                                    1120: "ks-Arab",
                                    1121: "ne-NP",
                                    1122: "fy-NL",
                                    1123: "ps-AF",
                                    1124: "fil-PH",
                                    1125: "dv-MV",
                                    1126: "bin-NG",
                                    1127: "ff-NG",
                                    1128: "ha-Latn-NG",
                                    1129: "ibb-NG",
                                    1130: "yo-NG",
                                    1131: "quz-BO",
                                    1132: "nso-ZA",
                                    1133: "ba-RU",
                                    1134: "lb-LU",
                                    1135: "kl-GL",
                                    1136: "ig-NG",
                                    1137: "kr-Latn-NG",
                                    1138: "om-ET",
                                    1139: "ti-ET",
                                    1140: "gn-PY",
                                    1141: "haw-US",
                                    1142: "la-VA",
                                    1143: "so-SO",
                                    1144: "ii-CN",
                                    1145: "pap-029",
                                    1146: "arn-CL",
                                    1148: "moh-CA",
                                    1150: "br-FR",
                                    1152: "ug-CN",
                                    1153: "mi-NZ",
                                    1154: "oc-FR",
                                    1155: "co-FR",
                                    1156: "gsw-FR",
                                    1157: "sah-RU",
                                    1158: "qut-GT",
                                    1159: "rw-RW",
                                    1160: "wo-SN",
                                    1164: "prs-AF",
                                    1165: "plt-MG",
                                    1166: "zh-yue-HK",
                                    1167: "tdd-Tale-CN",
                                    1168: "khb-Talu-CN",
                                    1169: "gd-GB",
                                    1170: "ku-Arab-IQ",
                                    1171: "quc-CO",
                                    1281: "qps-ploc",
                                    1534: "qps-ploca",
                                    2049: "ar-IQ",
                                    2051: "ca-ES-valencia",
                                    2052: "zh-CN",
                                    2055: "de-CH",
                                    2057: "en-GB",
                                    2058: "es-MX",
                                    2060: "fr-BE",
                                    2064: "it-CH",
                                    2065: "ja-Ploc-JP",
                                    2067: "nl-BE",
                                    2068: "nn-NO",
                                    2070: "pt-PT",
                                    2072: "ro-MD",
                                    2073: "ru-MD",
                                    2074: "sr-Latn-CS",
                                    2077: "sv-FI",
                                    2080: "ur-IN",
                                    2087: "Neither",
                                    2092: "az-Cyrl-AZ",
                                    2094: "dsb-DE",
                                    2098: "tn-BW",
                                    2107: "se-SE",
                                    2108: "ga-IE",
                                    2110: "ms-BN",
                                    2111: "kk-Latn-KZ",
                                    2115: "uz-Cyrl-UZ",
                                    2117: "bn-BD",
                                    2118: "pa-Arab-PK",
                                    2121: "ta-LK",
                                    2128: "mn-Mong-CN",
                                    2129: "bo-BT",
                                    2137: "sd-Arab-PK",
                                    2141: "iu-Latn-CA",
                                    2143: "tzm-Latn-DZ",
                                    2144: "ks-Deva-IN",
                                    2145: "ne-IN",
                                    2151: "ff-Latn-SN",
                                    2155: "quz-EC",
                                    2163: "ti-ER",
                                    2559: "qps-plocm",
                                    3072: "user",
                                    3073: "ar-EG",
                                    3076: "zh-HK",
                                    3079: "de-AT",
                                    3081: "en-AU",
                                    3082: "es-ES",
                                    3084: "fr-CA",
                                    3098: "sr-Cyrl-CS",
                                    3131: "se-FI",
                                    3152: "mn-Mong-MN",
                                    3153: "dz-BT",
                                    3167: "tmz-MA",
                                    3179: "quz-PE",
                                    4096: "user",
                                    4097: "ar-LY",
                                    4100: "zh-SG",
                                    4103: "de-LU",
                                    4105: "en-CA",
                                    4106: "es-GT",
                                    4108: "fr-CH",
                                    4122: "hr-BA",
                                    4155: "smj-NO",
                                    4191: "tzm-Tfng-MA",
                                    5121: "ar-DZ",
                                    5124: "zh-MO",
                                    5127: "de-LI",
                                    5129: "en-NZ",
                                    5130: "es-CR",
                                    5132: "fr-LU",
                                    5146: "bs-Latn-BA",
                                    5179: "smj-SE",
                                    6145: "ar-MA",
                                    6153: "en-IE",
                                    6154: "es-PA",
                                    6156: "fr-MC",
                                    6170: "sr-Latn-BA",
                                    6203: "sma-NO",
                                    7169: "ar-TN",
                                    7177: "en-ZA",
                                    7178: "es-DO",
                                    7180: "fr-029",
                                    7194: "sr-Cyrl-BA",
                                    7227: "sma-SE",
                                    8193: "ar-OM",
                                    8200: "Neither",
                                    8201: "en-JM",
                                    8202: "es-VE",
                                    8204: "fr-RE",
                                    8218: "bs-Cyrl-BA",
                                    8251: "sms-FI",
                                    9217: "ar-YE",
                                    9225: "en-029",
                                    9226: "es-CO",
                                    9228: "fr-CD",
                                    9242: "sr-Latn-RS",
                                    9275: "smn-FI",
                                    10241: "ar-SY",
                                    10249: "en-BZ",
                                    10250: "es-PE",
                                    10252: "fr-SN",
                                    10266: "sr-Cyrl-RS",
                                    11265: "ar-JO",
                                    11273: "en-TT",
                                    11274: "es-AR",
                                    11276: "fr-CM",
                                    11290: "sr-Latn-ME",
                                    12289: "ar-LB",
                                    12297: "en-ZW",
                                    12298: "es-EC",
                                    12300: "fr-CI",
                                    12314: "sr-Cyrl-ME",
                                    13313: "ar-KW",
                                    13321: "en-PH",
                                    13322: "es-CL",
                                    13324: "fr-ML",
                                    14337: "ar-AE",
                                    14345: "en-ID",
                                    14346: "es-UY",
                                    14348: "fr-MA",
                                    15361: "ar-BH",
                                    15369: "en-HK",
                                    15370: "es-PY",
                                    15372: "fr-HT",
                                    16385: "ar-QA",
                                    16393: "en-IN",
                                    16394: "es-BO",
                                    17409: "ar-Ploc-SA",
                                    17417: "en-MY",
                                    17418: "es-SV",
                                    18433: "ar-145",
                                    18441: "en-SG",
                                    18442: "es-HN",
                                    19465: "en-AE",
                                    19466: "es-NI",
                                    20489: "en-BH",
                                    20490: "es-PR",
                                    21513: "en-EG",
                                    21514: "es-US",
                                    22537: "en-JO",
                                    22538: "es-419",
                                    23561: "en-KW",
                                    23562: "es-CU",
                                    24585: "en-TR",
                                    25609: "en-YE",
                                    25626: "bs-Cyrl",
                                    26650: "bs-Latn",
                                    27674: "sr-Cyrl",
                                    28698: "sr-Latn",
                                    28731: "smn",
                                    29740: "az-Cyrl",
                                    29755: "sms",
                                    30724: "zh",
                                    30740: "nn",
                                    30746: "bs",
                                    30764: "az-Latn",
                                    30779: "sma",
                                    30783: "kk-Cyrl",
                                    30787: "uz-Cyrl",
                                    30800: "mn-Cyrl",
                                    30813: "iu-Cans",
                                    30815: "tzm-Tfng",
                                    31748: "zh-Hant",
                                    31764: "nb",
                                    31770: "sr",
                                    31784: "tg-Cyrl",
                                    31790: "dsb",
                                    31803: "smj",
                                    31807: "kk-Latn",
                                    31811: "uz-Latn",
                                    31814: "pa-Arab",
                                    31824: "mn-Mong",
                                    31833: "sd-Arab",
                                    31836: "chr-Cher",
                                    31837: "iu-Latn",
                                    31839: "tzm-Latn",
                                    31847: "ff-Latn",
                                    31848: "ha-Latn",
                                    31890: "ku-Arab",
                                    62190: "reserved",
                                    58380: "fr-015",
                                    61166: "reserved"
                                }
                            }.get(platform_id, {}).get(
                                language_id, "Unknown"
                            ) + f" (0x{hex(language_id)[2:].zfill(4)})"

                            name_id = self.buf.ru16()
                            entry["name"] = {
                                0: "Copyright notice",
                                1: "Font Family",
                                2: "Font Subfamily",
                                3: "Unique subfamily identification",
                                4: "Full name of the font",
                                5: "Version of the name table",
                                6: "PostScript name of the font",
                                7: "Trademark notice",
                                8: "Manufacturer name",
                                9:
                                "Designer; name of the designer of the typeface",
                                10: "Description of the typeface",
                                11: "URL of the font vendor",
                                12: "URL of the font designer",
                                13: "License description",
                                14: "License information URL",
                                15: "Reserved",
                                16: "Preferred Family",
                                17: "Preferred Subfamily",
                                18: "Compatible Full",
                                19: "Sample text",
                                20: "Defined by OpenType",
                                21: "Defined by OpenType",
                                22: "Defined by OpenType",
                                23: "Defined by OpenType",
                                24: "Defined by OpenType",
                                25: "Variations PostScript Name Prefix"
                            }.get(name_id, "Unknown"
                                  ) + f" (0x{hex(name_id)[2:].zfill(4)})"

                            text_length = self.buf.ru16()
                            entry["length"] = text_length
                            text_offset = self.buf.ru16()
                            entry["offset"] = text_offset

                            with self.buf:
                                self.buf.seek(offset + string_offset +
                                              text_offset)
                                text_length = ((text_length + 1) >> 1) << 1
                                entry["text"] = self.buf.rs(
                                    text_length, "utf-16be" if
                                    (platform_id in (0, 3)) else "latin-1")

                            table["data"]["entries"].append(entry)
                    case "post":
                        table["data"]["format"] = str(
                            self.buf.ru16()) + "." + str(self.buf.ru16())
                        table["data"]["italic-angle"] = str(
                            self.buf.ru16()) + "." + str(self.buf.ru16())
                        table["data"]["underline-position"] = self.buf.ri16()
                        table["data"]["underline-thickness"] = self.buf.ri16()
                        table["data"]["is-fixed-pitch"] = self.buf.ru32()
                        table["data"]["min-mem-type42"] = self.buf.ru32()
                        table["data"]["max-mem-type42"] = self.buf.ru32()
                        table["data"]["min-mem-type1"] = self.buf.ru32()
                        table["data"]["max-mem-type1"] = self.buf.ru32()
                    case "cmap":
                        table["data"]["version"] = self.buf.ru16()
                        table["data"]["subtable-count"] = self.buf.ru16()
                    case "gasp":
                        table["data"]["version"] = self.buf.ru16()
                        table["data"]["range-count"] = self.buf.ru16()
                    case "glyf" | "hmtx" | "loca" | "GDEF" | "GPOS" | "GSUB":
                        # not really parsable as it's the raw glyph data
                        pass
                    case _:
                        table["unknown"] = True

            meta["tables"].append(table)

        for table in meta["tables"]:
            if table["offset"] + table["length"] > self.buf.tell():
                self.buf.seek(table["offset"])
                self.buf.skip(table["length"] + 1)

        return meta
