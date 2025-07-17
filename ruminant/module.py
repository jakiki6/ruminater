modules = []


def register(cls):
    modules.append(cls)


class RuminantModule(object):

    def __init__(self, buf):
        self.buf = buf

    def identify(buf):
        return False

    def chew(self):
        pass
