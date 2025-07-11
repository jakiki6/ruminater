import magic, json, hashlib, re
from .. import module
from ..buf import *

mappings = {}

class EntryModule(module.RuminaterModule):
    def chew(self):
        meta = {}

        data_len = self.blob.size()

        data_type = magic.from_buffer(self.blob.peek(65536))
        self.blob.seek(0)

        h = hashlib.sha256()
        i = data_len
        while i > 0:
            h.update(self.blob.read(1<<24))
            i -= 1<<24
        self.blob.seek(0)
        data_hash = h.hexdigest()

        meta["length"] = data_len
        meta["hash-sha256"] = data_hash

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
