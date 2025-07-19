from . import modules
import argparse
import sys
import json
import tempfile


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

    args = parser.parse_args()

    if args.file == "-":
        args.file = "/dev/stdin"

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
            print(json.dumps(modules.chew(file), indent=2))
    else:
        with open(args.file, "rb") as file:
            print(json.dumps(modules.chew(file), indent=2))
