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
