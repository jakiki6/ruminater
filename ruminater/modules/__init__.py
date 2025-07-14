import json, hashlib, re
from .. import module
from ..buf import *

class EntryModule(module.RuminaterModule):
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
                    self.buf.cut()
                    meta["trailer"] = self.chew()
                break

        if not matched:
            meta |= {"type": "unknown"}

        return meta

def chew(blob):
    return EntryModule(Buf(blob)).chew()

from . import containers, images, videos, documents
