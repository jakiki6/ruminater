import io, struct

class Buf(object):
    def __init__(self, source):
        if isinstance(source, io.IOBase):
            self._file = source
        else:
            self._file = io.BytesIO(source)

        self._offset = 0

        pos = self.tell()
        self.seek(0, 2)
        self._size = self.tell()
        self.seek(pos)

        self.resetunit()
        self._target = self._size
        self._stack = []
        self._backup = []

    @classmethod
    def of(cls, source):
        if isinstance(source, cls):
            return source
        else:
            return cls(source)

    def available(self):
        return self._size - self.tell()

    def isend(self):
        return self.available() <= 0

    def size(self):
        return self._size

    def peek(self, l):
        pos = self.tell()
        data = self._file.read(l)
        self.seek(pos)
        return data

    def skip(self, l):
        if self.unit != None:
            self.unit = max(self.unit - l, 0)
            assert self.unit >= 0, f"unit overread by {-self.unit} byte{'s' if self.unit != -1 else ''}"
        self.seek(l, 1)

    def _checkunit(self):
        assert self.unit >= 0, f"unit overread by {-self.unit} byte{'s' if self.unit != -1 else ''}"

    def setunit(self, l):
        self.unit = l
        self._target = self.tell() + l
        self._checkunit()

    def skipunit(self):
        self.seek(self._target)
        self.unit = 0

    def readunit(self):
        return self.read(self.unit)

    def resetunit(self):
        self.unit = None

    def read(self, count=None):
        if count == None:
            self.unit = None
            return self._file.read()
        else:
            if self.unit != None:
                self.unit -= count
                self._checkunit()

            return self._file.read(count)

    def pushunit(self):
        self._stack.append((self.unit, self._target))

    def popunit(self):
        self.unit, t = self._stack.pop()
        if self.unit != None:
            self.unit = max(t - self._target, 0)
        self._target = t

    def backup(self):
        return (self.unit, self._target, self._stack, self.tell())

    def restore(self, bak):
        self.unit, self._target, self._stack, offset = bak
        self.seek(offset)

    def readline(self):
        line = self._file.readline()
        if self.unit != None:
            self.unit = max(self.unit - len(line), 0)
            self._checkunit()

        if len(line) >= 2 and line[-2] == 0x0d:
            line = line[:-2] + b"\n"

        return line

    def tell(self):
        return self._file.tell() - self._offset

    def seek(self, pos, t=0):
        if t == 0:
            pos += self._offset

        self._file.seek(pos, t)

    def sub(self, size):
        assert size <= self.size(), "sub buffer is bigger than host buffer"

        class SubWrapper(object):
            def __enter__(self2):
                self2._offset = self._offset
                self2._size = self._size
                self2._bak = self.backup()
                self._offset += self.tell()
                self._size = size

            def __exit__(self2, *args):
                self._offset = self2._offset
                self._size = self2._size
                self.restore(self2._bak)

        return SubWrapper()

    def subunit(self):
        return self.sub(self.unit)

    def cut(self):
        return self.sub(self.available())

    def ru8(self):
        return int.from_bytes(self.read(1), "big")

    def ru16(self):
        return int.from_bytes(self.read(2), "big")

    def ru24(self):
        return int.from_bytes(self.read(3), "big")

    def ru32(self):
        return int.from_bytes(self.read(4), "big")

    def ru64(self):
        return int.from_bytes(self.read(8), "big")

    def ri8(self):
        return int.from_bytes(self.read(1), "big", signed=True)

    def ri16(self):
        return int.from_bytes(self.read(2), "big", signed=True)

    def ri24(self):
        return int.from_bytes(self.read(3), "big", signed=True)

    def ri32(self):
        return int.from_bytes(self.read(4), "big", signed=True)

    def ri64(self):
        return int.from_bytes(self.read(8), "big", signed=True)

    def ru8l(self):
        return int.from_bytes(self.read(1), "little")

    def ru16l(self):
        return int.from_bytes(self.read(2), "little")

    def ru48l(self):
        return int.from_bytes(self.read(3), "little")

    def ru32l(self):
        return int.from_bytes(self.read(4), "little")

    def ru64l(self):
        return int.from_bytes(self.read(8), "little")

    def ri8l(self):
        return int.from_bytes(self.read(1), "little", signed=True)

    def ri16l(self):
        return int.from_bytes(self.read(2), "little", signed=True)

    def ri24l(self):
        return int.from_bytes(self.read(3), "little", signed=True)

    def ri32l(self):
        return int.from_bytes(self.read(4), "little", signed=True)

    def ri64l(self):
        return int.from_bytes(self.read(8), "little", signed=True)

    def rf32(self):
        return struct.unpack(">f", self.read(4))

    def rf64(self):
        return struct.unpack(">d", self.read(8))

    def rf32l(self):
        return struct.unpack("<f", self.read(4))

    def rf64l(self):
        return struct.unpack("<d", self.read(8))

    def rfp16(self):
        return self.ru16() / 256

    def rfp32(self):
        return self.ru32l() / 65536

    def rsfp16(self):
        return self.ri16l() / 256

    def rsfp32(self):
        return self.ri32l() / 65536

    def rfp16l(self):
        return self.ru16l() / 256

    def rfp32l(self):
        return self.ru32l() / 65536

    def rsfp16l(self):
        return self.ri16l() / 256

    def rsfp32l(self):
        return self.ri32l() / 65536

    def pu8(self):
        return int.from_bytes(self.peek(1), "big")

    def pu16(self):
        return int.from_bytes(self.peek(2), "big")

    def pu24(self):
        return int.from_bytes(self.peek(3), "big")

    def pu32(self):
        return int.from_bytes(self.peek(4), "big")

    def pu64(self):
        return int.from_bytes(self.peek(8), "big")

    def pi8(self):
        return int.from_bytes(self.peek(1), "big", signed=True)

    def pi16(self):
        return int.from_bytes(self.peek(2), "big", signed=True)

    def pi24(self):
        return int.from_bytes(self.peek(3), "big", signed=True)

    def pi32(self):
        return int.from_bytes(self.peek(4), "big", signed=True)

    def pi64(self):
        return int.from_bytes(self.peek(8), "big", signed=True)

    def pu8l(self):
        return int.from_bytes(self.peek(1), "little")

    def pu16l(self):
        return int.from_bytes(self.peek(2), "little")

    def pu24l(self):
        return int.from_bytes(self.peek(3), "little")

    def pu32l(self):
        return int.from_bytes(self.peek(4), "little")

    def pu64l(self):
        return int.from_bytes(self.peek(8), "little")

    def pi8l(self):
        return int.from_bytes(self.peek(1), "little", signed=True)

    def pi16l(self):
        return int.from_bytes(self.peek(2), "little", signed=True)

    def pi24l(self):
        return int.from_bytes(self.peek(3), "little", signed=True)

    def pi32l(self):
        return int.from_bytes(self.peek(4), "little", signed=True)

    def pi64l(self):
        return int.from_bytes(self.peek(8), "little", signed=True)

    def pf32(self):
        return struct.unpack(">f", self.peek(4))

    def pf64(self):
        return struct.unpack(">d", self.peek(8))

    def pf32l(self):
        return struct.unpack("<f", self.peek(4))

    def pf64l(self):
        return struct.unpack("<d", self.peek(8))

    def pfp16(self):
        return self.ru16() / 256

    def pfp32(self):
        return self.ru32l() / 65536

    def psfp16(self):
        return self.ri16l() / 256

    def psfp32(self):
        return self.ri32l() / 65536

    def pfp16l(self):
        return self.ru16l() / 256

    def pfp32l(self):
        return self.ru32l() / 65536

    def psfp16l(self):
        return self.ri16l() / 256

    def psfp32l(self):
        return self.ri32l() / 65536

    def rh(self, l):
        return self.read(l).hex()

    def ph(self, l):
        return self.peek(l).hex()

    def __getattr__(self, name):
        # Delegate everything else to the underlying file
        return getattr(self._file, name)

    def __enter__(self):
        self._backup.append(self.backup())

    def __exit__(self, *args):
        self.restore(self._backup.pop())

    def __iter__(self):
        return iter(self._file)

    def __next__(self):
        return next(self._file)

