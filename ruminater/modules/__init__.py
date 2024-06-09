import magic, json, hashlib
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

        if data_type.split(",")[0] in mappings:
            meta |= mappings[data_type.split(",")[0]](self.blob).chew()
        else:
            meta |= {"type": "blob", "libmagic-type": data_type}

        return meta

def chew(blob):
    return EntryModule(blob).chew()

from . import containers, images, videos, documents
