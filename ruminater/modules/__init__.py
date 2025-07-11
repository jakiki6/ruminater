import magic, json, hashlib, re
from .. import module
from ..buf import *

mappings = {}

class EntryModule(module.RuminaterModule):
    def chew(self):
        meta = {}

        data_type = magic.from_buffer(self.blob.peek(65536))
        meta["length"] = self.blob.size()

        matched = False
        for k, v in mappings.items():
            if re.match(k, data_type):
                meta |= v(self.blob).chew()
                matched = True

        if not matched:
            meta |= {"type": "blob", "libmagic-type": data_type}

        return meta

def chew(blob):
    return EntryModule(Buf(blob)).chew()

from . import containers, images, videos, documents
