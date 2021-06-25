#!/usr/bin/env python

"""Tests for `pysesameos2` package."""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from pysesameos2.crypto import AppKey, AppKeyFactory, BleCipher


class TestAppKeyFactory:
    def test_AppKeyFactory(self):
        assert isinstance(AppKeyFactory.get_instance(), AppKey)

        appkey1 = AppKeyFactory.get_instance()
        appkey2 = AppKeyFactory.get_instance()

        assert id(appkey1) == id(appkey2)


class TestAppKey:
    def test_AppKey_getPubkey(self):
        k = AppKeyFactory.get_instance()

        pk_bytes = k.getPubkey()
        fixed_header = bytes.fromhex(
            "3059301306072a8648ce3d020106082a8648ce3d03010703420004"
        )
        pk = serialization.load_der_public_key(fixed_header + pk_bytes)
        assert isinstance(pk, ec.EllipticCurvePublicKey)

    def test_AppKey_getAppToken(self):
        k = AppKeyFactory.get_instance()

        token = k.getAppToken()
        assert len(token) == 4
        assert isinstance(token, bytes)

    def test_AppKey_ecdh(self, monkeypatch):
        k = AppKeyFactory.get_instance()

        monkeypatch.setattr(
            k,
            "_secretKey",
            bytes.fromhex(
                "30770201010420abb8309e288941a3d0e86124f581390b90805635e27b32a2e3f094e900577b56a00a06082a8648ce3d030107a14403420004c351160b1446d96e92307bc3c05b37cf004f1b6e4e7bd712571a483b8cbd8e5e75a3b60b1aeef0fe17a7e120bf4175315f872440c27afec855c5b959fdf746d4"
            ),
        )
        peer_private_key = serialization.load_der_private_key(
            bytes.fromhex(
                "30770201010420328dde3315e0a21353ae277cb10a8c080131c2d82539788e2ce92135f635fba2a00a06082a8648ce3d030107a14403420004d422b28bafdc17a9af2a7e778aeb9f9b962da8044d16f0107ad8d2db605b0090fded0d7301fff24b3da3fe9126800be1ac046aca8144865f2e245fad32ecce5f"
            ),
            password=None,
        )

        shared_key = k.ecdh(
            peer_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )[27:]
        )

        assert (
            shared_key.hex()
            == "f7eeb4cec4fa0b427a9b8aec13b9a12179f04a2d0ac5b3f16728c303a1eefa84"
        )


class TestBleCipher:
    def test_BleCipher_decrypt(self, monkeypatch):
        c = BleCipher(
            session_key=bytes.fromhex("6df237e72cd41f63cf32451232bee545"),
            session_token=bytes.fromhex("1b20262a82169bc9"),
        )
        monkeypatch.setattr(c, "_decryptCounter", 1)

        enc_payload = bytes.fromhex("56469d110effbf33")
        # OpCode=Response, CmdItCode=BleItemCode.history, CmdOPCode=BleOpCode.read, CmdResultCode=BleCmdResultCode.notFound
        assert c.decrypt(cipher_bytes=enc_payload).hex() == "07040205"

    def test_BleCipher_encrypt(self):
        c = BleCipher(
            session_key=bytes.fromhex("6df237e72cd41f63cf32451232bee545"),
            session_token=bytes.fromhex("1b20262a82169bc9"),
        )

        # OpCode=BleOpCode.read, ItCode=BleItemCode.history, payload=bytes([1])
        plain_payload = bytes.fromhex("020401")
        assert c.encrypt(plain_bytes=plain_payload).hex() == "fed1862150bea9"
