# -*- coding: UTF-8 -*-
import hashlib
import base64 as b64


class EncryptLib(object):

    @staticmethod
    def _init_(data):
        return data.encode(encoding='UTF-8')

    def md5(self, data):
        return hashlib.md5(self._init_(data)).hexdigest()

    def sha1(self, data):
        return hashlib.sha1(self._init_(data)).hexdigest()

    def sha224(self, data):
        return hashlib.sha224(self._init_(data)).hexdigest()

    def sha256(self, data):
        return hashlib.sha256(self._init_(data)).hexdigest()

    def sha384(self, data):
        return hashlib.sha384(self._init_(data)).hexdigest()

    def sha512(self, data):
        return hashlib.sha512(self._init_(data)).hexdigest()

    def base64(self, data):
        return str(b64.b64encode(self._init_(data)), 'UTF-8')


ep = EncryptLib()
