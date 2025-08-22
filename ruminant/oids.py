import os

OIDS = {}

with open(os.path.join(os.path.dirname(__file__), "oids.txt"), "r") as file:
    rows = []
    for line in file.readlines():
        if line.startswith("#"):
            continue

        line = line[:-1].split(": ")
        rows.append((line[0], ": ".join(line[1:])))

    for row in rows:
        key = [int(x) for x in row[0].split(".")]

        root = OIDS
        for i in key[:-1]:
            if i not in root:
                root[i] = {"name": "?", "children": {}}

            root = root[i]["children"]

        if key[-1] not in root:
            root[key[-1]] = {"name": "?", "children": {}}

        root[key[-1]]["name"] = row[1]
