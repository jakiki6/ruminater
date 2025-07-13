import json

modules = []

def register(cls):
    modules.append(cls)

class RuminaterModule(object):
    def __init__(self, buf):
        self.buf = buf

    def identify(buf):
        return False

    def chew(self):
        pass
