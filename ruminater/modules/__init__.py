import magic, json, hashlib, re
from .. import module

mappings = {}

class EntryModule(module.RuminaterModule):
    def chew(self):
        data = self.blob.read()
        self.blob.seek(0)

        meta = {}

        data_type = magic.from_buffer(data)
        data_len = len(data)
        data_hash = hashlib.sha256(data).hexdigest()

        meta["length"] = data_len
        meta["hash-sha256"] = data_hash

        del data    # free RAM

        matched = False
        for k, v in mappings.items():
            if re.match(k, data_type):
                meta |= v(self.blob).chew()
                matched = True

        if not matched:
            meta |= {"type": "blob", "libmagic-type": data_type}

        return meta

def chew(blob):
    return EntryModule(blob).chew()

from . import containers, images, videos, documents
