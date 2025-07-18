from .. import module
from ..buf import Buf

to_extract = []
blob_id = 0


class EntryModule(module.RuminantModule):

    def chew(self):
        global blob_id

        meta = {}
        meta["blob-id"] = blob_id
        blob_id += 1

        offset = self.buf.tell()

        matched = False
        for m in module.modules:
            if m.identify(self.buf):
                rest = m(self.buf).chew()
                meta["length"] = self.buf.tell()
                meta |= rest

                matched = True

                if self.buf.available():
                    with self.buf.cut():
                        meta["trailer"] = self.chew()

                    self.buf.skip(self.buf.available())
                break

        if not matched:
            meta |= {"type": "unknown", "length": self.buf.size()}

        for k, v in to_extract:
            if k == meta["blob-id"]:
                with self.buf:
                    self.buf.resetunit()
                    self.buf.seek(offset)

                    with open(v, "wb") as file:
                        length = meta["length"]

                        while length:
                            blob = self.buf.read(min(1 << 24, length))
                            file.write(blob)
                            length -= len(blob)

        return meta


def chew(blob):
    return EntryModule(Buf.of(blob)).chew()


from . import containers, images, videos, documents  # noqa: F401,E402
