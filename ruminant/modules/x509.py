from .. import module, utils


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
        return buf.peek(2) == b"\x30\x82"

    def chew(self):
        meta = {}
        meta["type"] = "der"

        meta["data"] = utils.read_der(self.buf)

        return meta
