modules = []


def register(cls):
    modules.append(cls)
    return cls


class RuminantModule(object):

    def __init__(self, buf):
        self.buf = buf

    def identify(buf, ctx={}):
        return False

    def chew(self):
        self.buf.skip(self.buf.available())
        return {}
