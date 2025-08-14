from .. import module, utils, buf
import base64


@module.register
class PdfTimestampSignatureModule(module.RuminantModule):

    def identify(buf):
        with buf:
            buf.skip(27)
            return buf.peek(2) == b"\x30\x82"

    def chew(self):
        meta = {}
        meta["type"] = "pdf-timestamp-signature"

        self.buf.skip(27)
        meta["data"] = utils.read_der(self.buf)

        return meta


@module.register
class DerModule(module.RuminantModule):

    def identify(buf):
        return buf.pu16() & 0xfff0 == 0x3080

    def chew(self):
        meta = {}
        meta["type"] = "der"

        meta["data"] = utils.read_der(self.buf)

        return meta


@module.register
class PemModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(27) == b"-----BEGIN CERTIFICATE-----"

    def chew(self):
        meta = {}
        meta["type"] = "pem"

        self.buf.skip(27)

        content = b""
        while True:
            line = self.buf.rl()
            if line == b"-----END CERTIFICATE-----":
                break

            content += line

        while self.buf.peek(1) in (b"\r", b"\n"):
            self.buf.skip(1)

        meta["data"] = utils.read_der(buf.Buf(base64.b64decode(content)))

        return meta


@module.register
class PpgModule(module.RuminantModule):

    def identify(buf):
        return buf.peek(36) == b"-----BEGIN PGP PUBLIC KEY BLOCK-----" or (buf.pu8() in (0x85, 0x89) and buf.peek(4)[3] in (0x03, 0x04))

    def chew(self):
        meta = {}
        meta["type"] = "pgp"

        if self.buf.peek(1) == b"-":
            self.buf.skip(36)

            content = b""
            while True:
                line = self.buf.rl()
                if line == b"-----END PGP PUBLIC KEY BLOCK-----":
                    break

                content += line

            while self.buf.peek(1) in (b"\r", b"\n"):
                self.buf.skip(1)

            fd = buf.Buf(base64.b64decode(content))
        else:
            fd = self.buf

        meta["data"] = []
        while fd.available() > 0:
            meta["data"].append(utils.read_pgp(fd))

        return meta
