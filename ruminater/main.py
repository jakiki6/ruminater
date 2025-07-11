from . import modules
import sys, json

def main():
    if len(sys.argv) != 2:
        print(sys.argv[0], "<file>")
        exit(1)

    with open(sys.argv[1], "rb") as f:
        print(json.dumps(modules.chew(f), indent=2))
