import json, hashlib, re
from .. import module
from ..buf import *

class EntryModule(module.RuminaterModule):
    def chew(self):
        meta = {}

        meta["length"] = self.buf.size()

        matched = False
        for m in module.modules:
            if m.identify(self.buf):
                meta |= m(self.buf).chew()
                matched = True

        if not matched:
            meta |= {"type": "unknown"}

        return meta

def chew(blob):
    return EntryModule(Buf(blob)).chew()

from . import containers, images, videos, documents
