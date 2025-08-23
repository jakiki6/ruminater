import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import oids  # noqa: E402


def append_unknowns(root, todo, base=[]):
    for key, value in root.items():
        if value["name"] == "?":
            todo.append(base + [key])

        append_unknowns(value["children"], todo, base + [key])


if len(sys.argv) > 1:
    todo = [[int(y) for y in x.split(".")] for x in sys.argv[1:]]
else:
    todo = []
    append_unknowns(oids.OIDS, todo)


def insert(root, oid, name):
    if len(oid) == 1:
        if oid[0] not in root:
            root[oid[0]] = {"name": "?", "children": {}}

        root[oid[0]]["name"] = name
    else:
        if oid[0] not in root:
            root[oid[0]] = {"name": "?", "children": {}}

        insert(root[oid[0]]["children"], oid[1:], name)


try:
    for oid in todo:
        name = input(f"{'.'.join(str(x) for x in oid)}: ")

        if len(name.strip()) == 0:
            continue

        insert(oids.OIDS, oid, name)
except EOFError:
    pass


def walk(root, file, base):
    if root["name"] != "?":
        print(f"{'.'.join(str(x) for x in base)}: {root['name']}", file=file)

    for key in sorted(root["children"].keys()):
        walk(root["children"][key], file, base + [key])


with open(os.path.join(os.path.dirname(__file__), "oids.txt"), "w") as file:
    for key in sorted(oids.OIDS.keys()):
        walk(oids.OIDS[key], file, [key])
