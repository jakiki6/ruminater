import json, hashlib, re
from .. import module
from ..buf import *

class EntryModule(module.RuminantModule):
    def chew(self):
        meta = {}

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
            meta |= {
                "type": "unknown",
                "length": self.buf.size()
            }

        return meta

def chew(blob):
    return EntryModule(Buf.of(blob)).chew()

from . import containers, images, videos, documents
