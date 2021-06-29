#!/usr/bin/env python

"""Tests for `pysesameos2` package."""

import asyncio
import uuid
from unittest.mock import MagicMock

import pytest
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

from pysesameos2.ble import BLEAdvertisement
from pysesameos2.const import CHSesame2Intention, CHSesame2Status
from pysesameos2.crypto import BleCipher
from pysesameos2.device import CHDeviceKey, CHDevices, CHSesameLock
from pysesameos2.helper import CHProductModel


@pytest.fixture(autouse=True)
def ble_advertisement():
    bledevice = BLEDevice(
        "AA:BB:CC:11:22:33",
        "QpGK0YFUSv+9H/DN6IqN4Q",
        uuids=[
            "0000fd81-0000-1000-8000-00805f9b34fb",
        ],
        rssi=-60,
        manufacturer_data={1370: b"\x00\x00\x01"},
    )
    ble_advertisement = BLEAdvertisement(
        dev=bledevice, manufacturer_data={1370: b"\x00\x00\x01"}
    )
    return ble_advertisement


@pytest.fixture(autouse=True)
def ble_advertisement_not_registed_device():
    bledevice = BLEDevice(
        "AA:BB:CC:11:22:33",
        "QpGK0YFUSv+9H/DN6IqN4Q",
        uuids=[
            "0000fd81-0000-1000-8000-00805f9b34fb",
        ],
        rssi=-60,
        manufacturer_data={1370: b"\x00\x00\x00"},
    )
    ble_advertisement = BLEAdvertisement(
        dev=bledevice, manufacturer_data={1370: b"\x00\x00\x00"}
    )
    return ble_advertisement


class TestCHDeviceKey:
    def test_CHDeviceKey_secretKey_raises_exception_on_invalid_value(self):
        k = CHDeviceKey()

        with pytest.raises(TypeError) as excinfo:
            k.setSecretKey(123)
        assert "should be str or bytes" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            k.setSecretKey("FAKE")
        assert "non-hexadecimal number found" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            k.setSecretKey("FEED")
        assert "length should be 16" in str(excinfo.value)

    def test_CHDeviceKey_secretKey(self):
        k = CHDeviceKey()

        assert k.getSecretKey() is None

        secret_str = "34344f4734344b3534344f4934344f47"
        secret_bytes = bytes.fromhex(secret_str)

        assert k.setSecretKey(secret_bytes) is None
        assert k.getSecretKey() == secret_bytes

        assert k.setSecretKey(secret_str) is None
        assert k.getSecretKey() == secret_bytes

    def test_CHDeviceKey_sesame2PublicKey_raises_exception_on_invalid_value(self):
        k = CHDeviceKey()

        with pytest.raises(TypeError) as excinfo:
            k.setSesame2PublicKey(123)
        assert "should be str or bytes" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            k.setSesame2PublicKey("FAKE")
        assert "non-hexadecimal number found" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            k.setSesame2PublicKey("FEED")
        assert "length should be 64" in str(excinfo.value)

    def test_CHDeviceKey_sesame2PublicKey(self):
        k = CHDeviceKey()

        assert k.getSesame2PublicKey() is None

        pubkey_str = "34344f4734344b3534344f4934344f4734344b3534344f4934344f4734344b3534344f4934344f4734344b3534344f4934344f4734344b3534344f4934344f47"
        pubkey_bytes = bytes.fromhex(pubkey_str)

        assert k.setSesame2PublicKey(pubkey_bytes) is None
        assert k.getSesame2PublicKey() == pubkey_bytes

        assert k.setSesame2PublicKey(pubkey_str) is None
        assert k.getSesame2PublicKey() == pubkey_bytes

    def test_CHDeviceKey_getKeyIndex(self):
        k = CHDeviceKey()

        assert k.getKeyIndex() == bytes([0, 0])


class TestCHDevices:
    def test_CHDevices_deviceId_raises_exception_on_invalid_uuid(self):
        d = CHDevices()

        with pytest.raises(ValueError):
            d.setDeviceId("INVALID-UUID")

        with pytest.raises(TypeError):
            d.setDeviceId(12345)

    def test_CHDevices_deviceId(self):
        d = CHDevices()

        assert d.deviceId is None

        test_uuid = "42918AD1-8154-4AFF-BD1F-F0CDE88A8DE1"
        assert d.setDeviceId(test_uuid) is None
        assert d.deviceId == test_uuid

        test_uuid2 = uuid.UUID("42918AD1-8154-4AFF-BD1F-F0CDE88A8DE1")
        assert d.setDeviceId(test_uuid2) is None
        assert d.deviceId == str(test_uuid2).upper()

    def test_CHDevices_productModel_raises_exception_on_invalid_uuid(self):
        d = CHDevices()

        with pytest.raises(TypeError):
            d.setProductModel("INVALID-PRODUCT")

    def test_CHDevices_productModel(self):
        d = CHDevices()

        assert d.productModel is None

        test_model = CHProductModel.SS2
        assert d.setProductModel(test_model) is None
        assert d.productModel == test_model

    def test_CHDevices_rssi_raises_exception_on_invalid_value(self):
        d = CHDevices()

        with pytest.raises(TypeError):
            d.setRssi("INVALID-RSSI")

        with pytest.raises(TypeError):
            d.setRssi("-100")

    def test_CHDevices_rssi(self):
        d = CHDevices()

        assert d.getRssi() == -100

        assert d.setRssi(10) is None
        assert d.getRssi() == 10

    def test_CHDevices_device_status_raises_exception_on_invalid_value(self):
        d = CHDevices()

        with pytest.raises(TypeError):
            d.setDeviceStatus()

        with pytest.raises(TypeError):
            d.setDeviceStatus("INVALID-DEVICE-STATUS")

    def test_CHDevices_device_status(self):
        d = CHDevices()

        assert d.getDeviceStatus() == CHSesame2Status.NoBleSignal

        assert d.setDeviceStatus(CHSesame2Status.Locked) is None
        assert d.getDeviceStatus() == CHSesame2Status.Locked

    def test_CHDevices_device_status_callback_raises_exception_on_invalid_value(self):
        d = CHDevices()

        with pytest.raises(TypeError):
            d.setDeviceStatusCallback("INVALID-CALLBACK")

    def test_CHDevices_device_status_callback_with_none(self):
        d = CHDevices()

        assert d.setDeviceStatusCallback(None) is None
        assert d.setDeviceStatus(CHSesame2Status.NoBleSignal) is None
        assert d.setDeviceStatus(CHSesame2Status.Locked) is None

    def test_CHDevices_device_status_callback(self, mocker):
        d = CHDevices()

        assert d.setDeviceStatus(CHSesame2Status.NoBleSignal) is None

        class TestCallbackClass:
            def test_callback(self, device: CHDevices):
                assert device.getDeviceStatus() == CHSesame2Status.Locked

        test_callback_cls = TestCallbackClass()
        spy = mocker.spy(test_callback_cls, "test_callback")

        assert d.setDeviceStatusCallback(test_callback_cls.test_callback) is None

        assert d.setDeviceStatus(CHSesame2Status.NoBleSignal) is None
        assert spy.call_count == 0

        assert d.setDeviceStatus(CHSesame2Status.Locked) is None
        assert spy.call_count == 1

    def test_CHDevices_advertisement_raises_exception_on_invalid_value(self):
        d = CHDevices()

        with pytest.raises(TypeError):
            d.setAdvertisement("INVALID-ADV")

    def test_CHDevices_advertisement(self, ble_advertisement):
        d = CHDevices()

        assert d.setAdvertisement(None) is None
        assert d.getDeviceStatus() == CHSesame2Status.NoBleSignal
        assert d.getRssi() == -100

        assert d.setAdvertisement(ble_advertisement) is None
        assert d.getAdvertisement() == ble_advertisement
        assert d.productModel == CHProductModel.SS2
        assert d.getRssi() == -60
        assert d.deviceId == "42918AD1-8154-4AFF-BD1F-F0CDE88A8DE1"
        assert d.getRegistered()
        assert d.getDeviceStatus() == CHSesame2Status.ReceivedBle

    def test_CHDevices_advertisement_not_registed_device(
        self, ble_advertisement_not_registed_device
    ):
        d = CHDevices()

        with pytest.raises(RuntimeError) as excinfo:
            d.setAdvertisement(ble_advertisement_not_registed_device)
        assert "initial configuration needed" in str(excinfo.value)

    def test_CHDevices_registered_raises_exception_on_invalid_value(self):
        d = CHDevices()

        with pytest.raises(TypeError):
            d.setRegistered("TRUE")

    def test_CHDevices_registered(self):
        d = CHDevices()

        assert d.setRegistered(True) is None
        assert d.getRegistered() is True
        assert d.setRegistered(False) is None
        assert d.getRegistered() is False

    def test_CHDevices_key(self):
        d = CHDevices()

        assert isinstance(d.getKey(), CHDeviceKey)

    @pytest.mark.asyncio
    async def test_CHDevices_wait_for_login(self, event_loop):
        d = CHDevices()

        event_loop.call_later(3, d.setDeviceStatus(CHSesame2Status.Locked))
        assert await d.wait_for_login()


class TestCHSesameLock:
    def test_CHSesameLock_deviceUUID_raises_exception_on_invalid_uuid(self):
        d = CHSesameLock()

        with pytest.raises(ValueError):
            d.setDeviceUUID("INVALID-UUID")

    def test_CHSesameLock_deviceUUID(self):
        d = CHSesameLock()

        assert d.getDeviceUUID() is None

        test_uuid = "42918AD1-8154-4AFF-BD1F-F0CDE88A8DE1"
        assert d.setDeviceUUID(test_uuid) is None
        assert d.getDeviceUUID() == test_uuid

        test_uuid2 = uuid.UUID("42918AD1-8154-4AFF-BD1F-F0CDE88A8DE1")
        assert d.setDeviceUUID(test_uuid2) is None
        assert d.getDeviceUUID() == str(test_uuid2).upper()

    def test_CHSesameLock_intention_raises_exception_on_invalid_value(self):
        d = CHSesameLock()

        with pytest.raises(TypeError):
            d.setIntention("INVALID-INTENTION")

    def test_CHSesameLock_intention(self):
        d = CHSesameLock()

        assert d.getIntention() == CHSesame2Intention.idle
        assert d.setIntention(CHSesame2Intention.locking) is None
        assert d.getIntention() == CHSesame2Intention.locking

    def test_CHSesameLock_cipher_raises_exception_on_invalid_value(self):
        d = CHSesameLock()

        with pytest.raises(TypeError):
            d.setCipher("INVALID-CIPHER")

    def test_CHSesameLock_cipher(self):
        d = CHSesameLock()

        assert d.getCipher() is None
        assert d.setCipher(BleCipher(session_key="fake", session_token="fake")) is None
        assert isinstance(d.getCipher(), BleCipher)

    def test_CHSesameLock_SesameToken_raises_exception_on_invalid_value(self):
        d = CHSesameLock()

        with pytest.raises(TypeError):
            d.setSesameToken("INVALID-TOKEN")

    def test_CHSesameLock_SesameToken(self):
        d = CHSesameLock()

        assert d.setSesameToken(b"fake") is None
        assert d.getSesameToken() == b"fake"

    def test_CHSesameLock_CharacteristicTX_raises_exception_on_invalid_value(self):
        d = CHSesameLock()

        with pytest.raises(TypeError):
            d.setCharacteristicTX("INVALID-CHAR")

    def test_CHSesameLock_CharacteristicTX(self):
        d = CHSesameLock()

        assert d.getCharacteristicTX() is None

        mock_char = MagicMock(spec=BleakGATTCharacteristic)
        assert d.setCharacteristicTX(mock_char) is None
        assert d.getCharacteristicTX() == mock_char

    def test_CHSesameLock(self):
        d = CHSesameLock()

        test_uuid = "42918AD1-8154-4AFF-BD1F-F0CDE88A8DE1"
        assert d.setDeviceUUID(test_uuid) is None

        test_model = CHProductModel.SS2
        assert d.setProductModel(test_model) is None

        assert (
            str(d)
            == "CHSesameLock(deviceUUID=42918AD1-8154-4AFF-BD1F-F0CDE88A8DE1, deviceModel=CHProductModel.SS2)"
        )

    def test_CHSesameLock_key_raises_exception_on_invalid_value(self):
        d = CHSesameLock()

        with pytest.raises(TypeError):
            d.setKey("INVALID-KEY")

    def test_CHSesameLock_key(self):
        d = CHSesameLock()
        k = CHDeviceKey()

        assert d.setKey(k) is None
        assert d.getKey() == k
