from . import modules
import sys
import json


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "-":
        with open("/dev/stdin", "rb") as f:
            content = f.read()

        print(json.dumps(modules.chew(content), indent=2))
    else:
        with open(sys.argv[1], "rb") as f:
            print(json.dumps(modules.chew(f), indent=2))
