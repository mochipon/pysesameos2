#!/usr/bin/env python

"""Tests for `pysesameos2` package."""

import sys

import pytest

from pysesameos2.ble import (
    CHSesame2BlePublish,
    CHSesame2BleReceiver,
    CHSesame2BleTransmiter,
)
from pysesameos2.chsesame2 import CHSesame2, CHSesame2BleLoginResponse
from pysesameos2.const import BleCommunicationType, CHSesame2Intention, CHSesame2Status
from pysesameos2.crypto import BleCipher
from pysesameos2.device import CHDeviceKey
from pysesameos2.helper import (
    CHProductModel,
    CHSesame2MechSettings,
    CHSesame2MechStatus,
)

if sys.version_info[:2] < (3, 8):
    from asynctest import patch
else:
    from unittest.mock import patch


class TestCHSesame2BleLoginResponse:
    def test_CHSesame2BleLoginResponse_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleLoginResponse()

    def test_CHSesame2BleLoginResponse_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleLoginResponse("INVALID-DATA")

    def test_CHSesame2BleLoginResponse(self):
        r = CHSesame2BleLoginResponse(
            bytes.fromhex("f545d36001008001e30105034d0179026f029b035e03008016020002")
        )

        assert isinstance(r.getMechStatus(), CHSesame2MechStatus)
        assert r.getMechStatus().isInLockRange()

        assert isinstance(r.getMechSetting(), CHSesame2MechSettings)
        assert r.getMechSetting().isConfigured


class TestCHSesame2:
    def test_CHSesame2_RxBuffer(self):
        s = CHSesame2()

        ble_receiver = CHSesame2BleReceiver()

        assert s.setRxBuffer(ble_receiver) is None
        assert s.getRxBuffer() == ble_receiver

    def test_CHSesame2_TxBuffer(self):
        s = CHSesame2()

        segment_type = BleCommunicationType.plaintext
        data = bytes.fromhex("feedfeedfeedfeedfeedfeedfeedfeed")
        ble_transmitter = CHSesame2BleTransmiter(segment_type, data)

        assert s.setTxBuffer(ble_transmitter) is None
        assert s.getTxBuffer() == ble_transmitter

    def test_CHSesame2_MechStatus_exception_on_emtry_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2MechStatus()

    def test_CHSesame2_MechStatus_raises_exception_on_invalid_argument(self):
        with pytest.raises(ValueError):
            CHSesame2MechStatus("INVALID")

        with pytest.raises(TypeError):
            CHSesame2MechStatus(10)

        s = CHSesame2()
        with pytest.raises(TypeError):
            s.setMechStatus("INVALID")

    def test_CHSesame2_MechStatus_idle_before_setMechSetting(self):
        s = CHSesame2()

        status = CHSesame2MechStatus("5d0300801c020002")
        assert s.setMechStatus(status) is None
        assert s.getMechStatus() == status
        assert s.getIntention() == CHSesame2Intention.idle

    def test_CHSesame2_MechStatus_idle(self):
        s = CHSesame2()
        s.setMechSetting(CHSesame2MechSettings("e30105034d0179026f029b03"))

        status = CHSesame2MechStatus("5d0300801c020002")
        assert s.setMechStatus(status) is None
        assert s.getMechStatus() == status
        assert s.getIntention() == CHSesame2Intention.idle

    def test_CHSesame2_MechStatus_unlocking_before_setMechSetting(self):
        s = CHSesame2()

        status = CHSesame2MechStatus("5d03050326020002")
        assert s.setMechStatus(status) is None
        assert s.getIntention() == CHSesame2Intention.movingToUnknownTarget

    def test_CHSesame2_MechStatus_unlocking(self):
        s = CHSesame2()
        s.setMechSetting(CHSesame2MechSettings("e30105034d0179026f029b03"))
        s.setMechStatus(CHSesame2MechStatus("5d03050326020002"))

        assert s.getIntention() == CHSesame2Intention.unlocking

    def test_CHSesame2_MechStatus_locking(self):
        s = CHSesame2()
        s.setMechSetting(CHSesame2MechSettings("e30105034d0179026f029b03"))
        s.setMechStatus(CHSesame2MechStatus("5c03e301f0020004"))

        assert s.getIntention() == CHSesame2Intention.locking

    def test_CHSesame2_MechSetting_raises_exception_on_invalid_argument(self):
        s = CHSesame2()
        with pytest.raises(TypeError):
            s.setMechSetting("INVALID")

    @pytest.mark.asyncio
    async def test_CHSesame2_loginSesame(self):
        s = CHSesame2()
        s.setSesameToken(bytes.fromhex("ffffffff"))

        k = CHDeviceKey()
        k.setSecretKey("34344f4734344b3534344f4934344f47")
        k.setSesame2PublicKey(
            "4beeaef8baabbd0198d606847364dfe3c324552d45fab9e538a1af8e04729279000644fce039621d3ae37303379c1114efbc8186bd7229093caae446751e7ef6"
        )
        s.setKey(k)

        with patch("pysesameos2.chsesame2.CHSesame2.transmit") as transmit:

            async def _transmit(*args, **kwargs):
                pass

            transmit.side_effect = _transmit
            assert (await s.loginSesame()) is None

    def test_CHSesame2_onConnectionStateChange(self):
        s = CHSesame2()
        assert s.onConnectionStateChange("BaseBleakClient") is None
        assert s.getDeviceStatus() == CHSesame2Status.NoBleSignal

    @pytest.mark.asyncio
    async def test_CHSesame2_onCharacteristicChanged_plaintext_publish(self):
        s = CHSesame2()
        s.setRegistered(True)

        with patch("pysesameos2.chsesame2.CHSesame2.loginSesame") as login_sesame:
            assert (
                await s.onCharacteristicChanged(10, bytearray.fromhex("03080effffffff"))
            ) is None
        login_sesame.assert_called_once()
        assert s.getSesameToken().hex() == "ffffffff"

    @pytest.mark.asyncio
    async def test_CHSesame2_onCharacteristicChanged_ciphertext_without_setCipher(self):
        s = CHSesame2()

        assert (
            await s.onCharacteristicChanged(
                10, bytearray.fromhex("01ffffffffffffffffffffffffffffffffffffff")
            )
        ) is None

        with pytest.raises(RuntimeError):
            await s.onCharacteristicChanged(
                10, bytearray.fromhex("04ffffffffffffffffffffffffffffffffff")
            )

    @pytest.mark.asyncio
    async def test_CHSesame2_onCharacteristicChanged_ciphertext_login_success_with_non_configured_device(
        self,
    ):
        s = CHSesame2()

        with patch("pysesameos2.crypto.BleCipher", spec=BleCipher) as ble_cipher:
            s.setCipher(ble_cipher)
            ble_cipher.decrypt.return_value = bytes.fromhex(
                "07020500f545d360ffffffffffffffffffffffffffffffffffffffffffffffff"
            )

            assert (
                await s.onCharacteristicChanged(10, bytearray.fromhex("050702"))
            ) is None
            assert s.getDeviceStatus() == CHSesame2Status.NoSettings

    @pytest.mark.asyncio
    async def test_CHSesame2_onCharacteristicChanged_ciphertext_login_success(self):
        s = CHSesame2()

        with patch("pysesameos2.crypto.BleCipher", spec=BleCipher) as ble_cipher:
            s.setCipher(ble_cipher)
            ble_cipher.decrypt.return_value = bytes.fromhex(
                "07020500f545d36001008001e30105034d0179026f029b035e03008016020002"
            )

            assert (
                await s.onCharacteristicChanged(10, bytearray.fromhex("050702"))
            ) is None
            assert s.getDeviceStatus() == CHSesame2Status.Locked

    @pytest.mark.asyncio
    async def test_CHSesame2_onGattSesamePublish_initial_with_non_registered_device(
        self,
    ):
        s = CHSesame2()
        s.setRegistered(False)

        publish_payload = CHSesame2BlePublish(bytes.fromhex("0effffffff"))

        with pytest.raises(NotImplementedError):
            await s.onGattSesamePublish(publish_payload)

    @pytest.mark.asyncio
    async def test_CHSesame2_onGattSesamePublish_initial_with_registered_device(self):
        s = CHSesame2()
        s.setRegistered(True)

        publish_payload = CHSesame2BlePublish(bytes.fromhex("0effffffff"))

        with patch("pysesameos2.chsesame2.CHSesame2.loginSesame") as login_sesame:
            assert (await s.onGattSesamePublish(publish_payload)) is None
        login_sesame.assert_called_once()

        assert s.getSesameToken().hex() == "ffffffff"

    @pytest.mark.asyncio
    async def test_CHSesame2_onGattSesamePublish_mechStatus(self):
        s = CHSesame2()
        s.setProductModel(CHProductModel.SS2)

        publish_payload = CHSesame2BlePublish(bytes.fromhex("5160030080f3ff0002"))

        assert (await s.onGattSesamePublish(publish_payload)) is None
        assert str(s.getMechStatus()) == str(
            CHSesame2MechStatus(rawdata="60030080f3ff0002")
        )
        assert s.getDeviceStatus() == CHSesame2Status.Locked

        assert (
            str(s)
            == "CHSesame2(deviceUUID=None, deviceModel=CHProductModel.SS2, mechStatus=CHSesame2MechStatus(Battery=100% (6.08V), isInLockRange=True, isInUnlockRange=False, Position=-13))"
        )

    @pytest.mark.asyncio
    async def test_CHSesame2_onGattSesamePublish_mechSetting(self):
        s = CHSesame2()

        publish_payload = CHSesame2BlePublish(
            bytes.fromhex("50efff1c0159ff85008600b201")
        )

        assert (await s.onGattSesamePublish(publish_payload)) is None
        assert str(s.getMechSetting()) == str(
            CHSesame2MechSettings(rawdata="efff1c0159ff85008600b201")
        )

    @pytest.mark.asyncio
    async def test_CHSesame2_connect_raises_exception_before_setAdvertisement(self):
        s = CHSesame2()
        with pytest.raises(RuntimeError):
            await s.connect()

    @pytest.mark.asyncio
    async def test_CHSesame2_loginSesame_raises_exception_before_setSesameToken(self):
        s = CHSesame2()
        with pytest.raises(RuntimeError):
            await s.loginSesame()

    @pytest.mark.asyncio
    async def test_CHSesame2_lock_raises_exception_on_no_device_connenction(self):
        s = CHSesame2()
        with pytest.raises(RuntimeError):
            await s.lock()

    @pytest.mark.asyncio
    async def test_CHSesame2_lock(self):
        s = CHSesame2()
        s.setDeviceStatus(CHSesame2Status.Unlocked)

        assert (await s.lock()) is None

    @pytest.mark.asyncio
    async def test_CHSesame2_unlock_raises_exception_on_no_device_connenction(self):
        s = CHSesame2()
        with pytest.raises(RuntimeError):
            await s.unlock()

    @pytest.mark.asyncio
    async def test_CHSesame2_unlock(self):
        s = CHSesame2()
        s.setDeviceStatus(CHSesame2Status.Locked)

        assert (await s.unlock()) is None

    @pytest.mark.asyncio
    async def test_CHSesame2_toggle_raises_exception_on_no_device_connenction(self):
        s = CHSesame2()
        with pytest.raises(RuntimeError):
            await s.toggle()

    @pytest.mark.asyncio
    async def test_CHSesame2_toggle_raises_exception_before_setMechStatus(self):
        s = CHSesame2()
        s.setDeviceStatus(CHSesame2Status.Locked)
        with pytest.raises(RuntimeError):
            await s.toggle()

    @pytest.mark.asyncio
    async def test_CHSesame2_toggle_to_unlocking(self):
        s = CHSesame2()
        s.setDeviceStatus(CHSesame2Status.Locked)
        s.setMechStatus(CHSesame2MechStatus(rawdata="60030080f3ff0002"))

        with patch("pysesameos2.chsesame2.CHSesame2.unlock") as unlock:
            assert (await s.toggle()) is None
        unlock.assert_called_once()

    @pytest.mark.asyncio
    async def test_CHSesame2_toggle_to_locking(self):
        s = CHSesame2()
        s.setDeviceStatus(CHSesame2Status.Unlocked)
        s.setMechStatus(CHSesame2MechStatus(rawdata="5c030503e3020004"))

        with patch("pysesameos2.chsesame2.CHSesame2.lock") as lock:
            assert (await s.toggle()) is None
        lock.assert_called_once()

    # TODO: Develop tests for the methods which relate to BleakClient.
