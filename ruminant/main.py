from . import modules
import argparse
import sys
import json


def main():
    parser = argparse.ArgumentParser(description="Ruminant parser")

    parser.add_argument("file", default="-", help="File to parse (default: -)")

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

    with open(args.file, "rb") as file:
        print(json.dumps(modules.chew(file), indent=2))
