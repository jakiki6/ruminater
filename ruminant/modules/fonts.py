from .. import module


@module.register
class TrueTypeModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(5) == b"\x00\x01\x00\x00\x00" or buf.peek(4) == b"OTTO"

    def chew(self):
        meta = {}
        meta["type"] = "truetype"

        self.buf.skip(4 if self.buf.pu8() else 5)

        num_tables = self.buf.ru16()
        meta["table-count"] = num_tables
        meta["search-range"] = self.buf.ru16()
        meta["entry-selector"] = self.buf.ru16()
        meta["range-shift"] = self.buf.ru16()

        meta["tables"] = []
        for i in range(0, num_tables):
            table = {}

            table["tag"] = self.buf.rs(4)
            table["checksum"] = self.buf.rh(4)
            table["offset"] = self.buf.ru32()
            table["length"] = self.buf.ru32()

            meta["tables"].append(table)

        return meta
