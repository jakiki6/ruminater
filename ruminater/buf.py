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

        self.unit = (1<<64) - 1
        self._target = self._size
        self._stack = []

    def available(self):
        return self._size - self.tell()

    def isend(self):
        return self.available() <= 0

    def size(self):
        return self._size

    def peek(self, l):
        pos = self._file.tell()
        data = self._file.read(l)
        self._file.seek(pos)
        return data

    def skip(self, l):
        self.unit = max(self.unit - l, 0)
        self.seek(l, 1)

    def setunit(self, l):
        self.unit = l
        self._target = self.tell() + l

    def skipunit(self):
        self.seek(self._target)
        self.unit = 0

    def readunit(self):
        return self.read(self.unit)

    def read(self, count=None):
        if count == None:
            self.unit = 0
            return self._file.read()
        else:
            self.unit -= count
            assert self.unit >= 0, f"unit overread by {-self.unit} byte{'s' if self.unit != -1 else ''}"

            return self._file.read(count)

    def pushunit(self):
        self._stack.append(self._target)

    def popunit(self):
        t = self._stack.pop()
        self.unit = max(t - self._target, 0)
        self._target = t

    def backup(self):
        return (self.unit, self._target, self._stack)

    def restore(self, bak):
        self.unit, self._target, self._stack = bak

    def readline(self):
        line = self._file.readline()
        self.unit = max(self.unit - len(line), 0)

        if len(line) >= 2 and line[-2] == 0x0d:
            line = line[:-2] + b"\n"

        return line

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

