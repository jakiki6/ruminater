from . import modules
from .buf import Buf
import argparse
import sys
import json
import tempfile
import os


def process(file, walk):
    if not walk:
        print(json.dumps(modules.chew(file), indent=2))
        return

    buf = Buf(file)
    unknown = 0

    data = []
    while buf.available():
        entry = None

        with buf:
            try:
                entry = modules.chew(file, True)
                assert entry["type"] != "unknown"
            except Exception:
                entry = None

        if entry is not None:
            if unknown > 0:
                data.append({
                    "type": "unknown",
                    "length": unknown,
                    "offset": buf.tell() - unknown,
                    "blob-id": modules.blob_id
                })
                modules.blob_id += 1
                unknown = 0

            data.append(entry)
            buf.skip(entry["length"])
        else:
            unknown += 1
            buf.skip(1)

    if unknown > 0:
        data.append({
            "type": "unknown",
            "length": unknown,
            "offset": buf.tell() - unknown,
            "blob-id": modules.blob_id
        })

    for entry in data:
        for k, v in modules.to_extract:
            if k == entry["blob-id"]:
                buf.seek(entry["offset"])
                with open(v, "wb") as file:
                    length = entry["length"]

                    while length:
                        blob = buf.read(min(1 << 24, length))
                        file.write(blob)
                        length -= len(blob)

    print(
        json.dumps({
            "type": "walk",
            "length": buf.size(),
            "entries": data
        },
                   indent=2))


def main():
    parser = argparse.ArgumentParser(description="Ruminant parser")

    parser.add_argument("file",
                        default="-",
                        nargs="?",
                        help="File to parse (default: -)")

    parser.add_argument(
        "--extract",
        "-e",
        nargs=2,
        metavar=("ID", "FILE"),
        action="append",
        help="Extract blob with given ID to FILE (can be repeated)")

    parser.add_argument(
        "--walk",
        "-w",
        action="store_true",
        help="Walk the file binwalk-style and look for parsable data")

    parser.add_argument("--extract-all",
                        action="store_true",
                        help="Extract all blobs to blobs/{id}.bin")

    args = parser.parse_args()

    if args.file == "-":
        args.file = "/dev/stdin"

    if args.extract_all:
        modules.extract_all = True
        if not os.path.isdir("blobs"):
            os.mkdir("blobs")

    if args.extract is not None:
        for k, v in args.extract:
            try:
                modules.to_extract.append((int(k), v))
            except ValueError:
                print(f"Cannot parse blob ID {k}", file=sys.stderr)
                exit(1)

    if args.file == "/dev/stdin":
        file = tempfile.TemporaryFile()
        with open("/dev/stdin", "rb") as f:
            while True:
                blob = f.read(1 << 24)
                if len(blob) == 0:
                    break

                file.write(blob)

        file.seek(0)
        with file:
            process(file, args.walk)
    else:
        with open(args.file, "rb") as file:
            process(file, args.walk)
