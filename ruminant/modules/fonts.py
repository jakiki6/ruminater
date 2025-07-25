from .. import module


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
                    case _:
                        table["unknown"] = True

            meta["tables"].append(table)

        for table in meta["tables"]:
            if table["offset"] + table["length"] > self.buf.tell():
                self.buf.seek(table["offset"])
                self.buf.skip(table["length"] + 1)

        return meta
