import io

class Buf(object):
    def __init__(self, source):
        if isinstance(source, io.IOBase):
            self._file = source
        else:
            self._file = io.BytesIO(source)

        pos = self.tell()
        self.seek(0, 2)
        self._size = self.tell()
        self.seek(pos)

        self.unit = 0

    def available(self):
        return self._size - self.tell()

    def isend(self):
        return self.available() <= 0

    def size(self):
        return self._size

    def peek(self, l):
        pos = self.tell()
        data = self.read(l)
        self.seek(pos)
        return data

    def skip(self, l):
        self.seek(l, 1)

    def set_unit(self, l):
        self.unit = l

    def skipunit(self):
        self.skip(self.unit)
        self.unit = 0

    def readunit(self):
        return self.read(self.unit)

    def read(self, count=None):
        if count == None:
            self.unit = 0
            return self._file.read()
        else:
            self.unit = max(self.unit - count, 0)
            return self._file.read(count)

    def __getattr__(self, name):
        # Delegate everything else to the underlying file
        return getattr(self._file, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._file.__exit__(exc_type, exc_val, exc_tb)

    def __iter__(self):
        return iter(self._file)

    def __next__(self):
        return next(self._file)

