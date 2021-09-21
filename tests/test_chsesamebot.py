#!/usr/bin/env python

"""Tests for `pysesameos2` package."""

import sys

import pytest

from pysesameos2.ble import (
    CHSesame2BlePublish,
    CHSesame2BleReceiver,
    CHSesame2BleTransmiter,
)
from pysesameos2.chsesamebot import CHSesameBot, CHSesameBotBleLoginResponse
from pysesameos2.const import BleCommunicationType, CHSesame2Intention, CHSesame2Status
from pysesameos2.crypto import BleCipher
from pysesameos2.device import CHDeviceKey
from pysesameos2.helper import (
    CHProductModel,
    CHSesameBotButtonMode,
    CHSesameBotMechSettings,
    CHSesameBotMechStatus,
    CHSesameBotUserPreDir,
)

if sys.version_info[:2] < (3, 8):
    from asynctest import patch
else:
    from unittest.mock import patch


class TestCHSesameBotBleLoginResponse:
    def test_CHSesameBotBleLoginResponse_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHSesameBotBleLoginResponse()

    def test_CHSesameBotBleLoginResponse_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHSesameBotBleLoginResponse("INVALID-DATA")

    def test_CHSesameBotBleLoginResponse(self):
        r = CHSesameBotBleLoginResponse(
            bytes.fromhex("4b41fe6000008001010a0a0a140f0000000000005803000000000004")
        )

        assert isinstance(r.getMechStatus(), CHSesameBotMechStatus)
        assert r.getMechStatus().getMotorStatus() == 0

        assert isinstance(r.getMechSetting(), CHSesameBotMechSettings)
        assert r.getMechSetting().getUserPrefDir() == CHSesameBotUserPreDir.reversed
        assert r.getMechSetting().getLockSecConfig().getLockSec() == 10
        assert r.getMechSetting().getLockSecConfig().getUnlockSec() == 10
        assert r.getMechSetting().getLockSecConfig().getClickLockSec() == 10
        assert r.getMechSetting().getLockSecConfig().getClickHoldSec() == 20
        assert r.getMechSetting().getLockSecConfig().getClickUnlockSec() == 15
        assert r.getMechSetting().getButtonMode() == CHSesameBotButtonMode.click


class TestCHSesameBot:
    def test_CHSesameBot_RxBuffer(self):
        s = CHSesameBot()

        ble_receiver = CHSesame2BleReceiver()

        assert s.setRxBuffer(ble_receiver) is None
        assert s.getRxBuffer() == ble_receiver

    def test_CHSesameBot_TxBuffer(self):
        s = CHSesameBot()

        segment_type = BleCommunicationType.plaintext
        data = bytes.fromhex("feedfeedfeedfeedfeedfeedfeedfeed")
        ble_transmitter = CHSesame2BleTransmiter(segment_type, data)

        assert s.setTxBuffer(ble_transmitter) is None
        assert s.getTxBuffer() == ble_transmitter

    def test_CHSesameBot_MechStatus_exception_on_emtry_arguments(self):
        with pytest.raises(TypeError):
            CHSesameBotMechStatus()

    def test_CHSesameBot_MechStatus_raises_exception_on_invalid_argument(self):
        with pytest.raises(ValueError):
            CHSesameBotMechStatus("INVALID")

        with pytest.raises(TypeError):
            CHSesameBotMechStatus(10)

        s = CHSesameBot()
        with pytest.raises(TypeError):
            s.setMechStatus("INVALID")

    def test_CHSesameBot_MechStatus_idle_as_initial_status(self):
        s = CHSesameBot()
        assert s.getIntention() == CHSesame2Intention.idle

    def test_CHSesameBot_MechStatus_idle(self):
        s = CHSesameBot()

        status = CHSesameBotMechStatus("5703000000000004")
        assert s.setMechStatus(status) is None
        assert s.getMechStatus() == status
        assert s.getIntention() == CHSesame2Intention.idle

    def test_CHSesameBot_MechStatus_unlocking(self):
        s = CHSesameBot()
        s.setMechStatus(CHSesameBotMechStatus("5503000003000004"))

        assert s.getIntention() == CHSesame2Intention.unlocking

    def test_CHSesameBot_MechStatus_locking(self):
        s = CHSesameBot()
        s.setMechStatus(CHSesameBotMechStatus("5703000001000002"))

        assert s.getIntention() == CHSesame2Intention.locking

    def test_CHSesameBot_MechStatus_holding(self):
        s = CHSesameBot()
        s.setMechStatus(CHSesameBotMechStatus("5503000002000002"))

        assert s.getIntention() == CHSesame2Intention.holding

    def test_CHSesameBot_MechStatus_movingToUnknownTarget(self):
        s = CHSesameBot()
        s.setMechStatus(CHSesameBotMechStatus("550300000f000002"))

        assert s.getIntention() == CHSesame2Intention.movingToUnknownTarget

    def test_CHSesameBot_MechSetting_raises_exception_on_invalid_argument(self):
        s = CHSesameBot()
        with pytest.raises(TypeError):
            s.setMechSetting("INVALID")

    @pytest.mark.asyncio
    async def test_CHSesameBot_loginSesame(self):
        s = CHSesameBot()
        s.setSesameToken(bytes.fromhex("ffffffff"))

        k = CHDeviceKey()
        k.setSecretKey("34344f4734344b3534344f4934344f47")
        k.setSesame2PublicKey(
            "4beeaef8baabbd0198d606847364dfe3c324552d45fab9e538a1af8e04729279000644fce039621d3ae37303379c1114efbc8186bd7229093caae446751e7ef6"
        )
        s.setKey(k)

        with patch("pysesameos2.chsesamebot.CHSesameBot.transmit") as transmit:

            async def _transmit(*args, **kwargs):
                pass

            transmit.side_effect = _transmit
            assert (await s.loginSesame()) is None

    def test_CHSesameBot_onConnectionStateChange(self):
        s = CHSesameBot()
        assert s.onConnectionStateChange("BaseBleakClient") is None
        assert s.getDeviceStatus() == CHSesame2Status.NoBleSignal

    @pytest.mark.asyncio
    async def test_CHSesameBot_onCharacteristicChanged_plaintext_publish(self):
        s = CHSesameBot()
        s.setRegistered(True)

        with patch("pysesameos2.chsesamebot.CHSesameBot.loginSesame") as login_sesame:
            assert (
                await s.onCharacteristicChanged(10, bytearray.fromhex("03080effffffff"))
            ) is None
        login_sesame.assert_called_once()
        assert s.getSesameToken().hex() == "ffffffff"

    @pytest.mark.asyncio
    async def test_CHSesameBot_onCharacteristicChanged_ciphertext_without_setCipher(
        self,
    ):
        s = CHSesameBot()

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
    async def test_CHSesameBot_onCharacteristicChanged_ciphertext_login_success(self):
        s = CHSesameBot()

        with patch("pysesameos2.crypto.BleCipher", spec=BleCipher) as ble_cipher:
            s.setCipher(ble_cipher)
            ble_cipher.decrypt.return_value = bytes.fromhex(
                "07020500e845fe6000008001010a0a0a140f0000000000005503000000000004"
            )

            assert (
                await s.onCharacteristicChanged(10, bytearray.fromhex("050702"))
            ) is None
            assert s.getIntention() == CHSesame2Intention.idle

    @pytest.mark.asyncio
    async def test_CHSesameBot_onGattSesamePublish_initial_with_non_registered_device(
        self,
    ):
        s = CHSesameBot()
        s.setRegistered(False)

        publish_payload = CHSesame2BlePublish(bytes.fromhex("0effffffff"))

        with pytest.raises(NotImplementedError):
            await s.onGattSesamePublish(publish_payload)

    @pytest.mark.asyncio
    async def test_CHSesameBot_onGattSesamePublish_initial_with_registered_device(self):
        s = CHSesameBot()
        s.setRegistered(True)

        publish_payload = CHSesame2BlePublish(bytes.fromhex("0effffffff"))

        with patch("pysesameos2.chsesamebot.CHSesameBot.loginSesame") as login_sesame:
            assert (await s.onGattSesamePublish(publish_payload)) is None
        login_sesame.assert_called_once()

        assert s.getSesameToken().hex() == "ffffffff"

    @pytest.mark.asyncio
    async def test_CHSesameBot_onGattSesamePublish_mechStatus(self):
        s = CHSesameBot()
        s.setProductModel(CHProductModel.SesameBot1)

        publish_payload = CHSesame2BlePublish(bytes.fromhex("515503000000000102"))

        assert (await s.onGattSesamePublish(publish_payload)) is None
        assert str(s.getMechStatus()) == str(
            CHSesameBotMechStatus(rawdata="5503000000000102")
        )
        assert s.getDeviceStatus() == CHSesame2Status.Locked

        assert (
            str(s)
            == "CHSesameBot(deviceUUID=None, deviceModel=CHProductModel.SesameBot1, mechStatus=CHSesameBotMechStatus(Battery=100% (3.00V), motorStatus=0))"
        )

    @pytest.mark.asyncio
    async def test_CHSesameBot_onGattSesamePublish_mechSetting(self):
        s = CHSesameBot()

        publish_payload = CHSesame2BlePublish(
            bytes.fromhex("50010a0a0a140f000000000000")
        )

        assert (await s.onGattSesamePublish(publish_payload)) is None
        assert str(s.getMechSetting()) == str(
            CHSesameBotMechSettings(rawdata="010a0a0a140f000000000000")
        )

    @pytest.mark.asyncio
    async def test_CHSesameBot_connect_raises_exception_before_setAdvertisement(self):
        s = CHSesameBot()
        with pytest.raises(RuntimeError):
            await s.connect()

    @pytest.mark.asyncio
    async def test_CHSesameBot_loginSesame_raises_exception_before_setSesameToken(self):
        s = CHSesameBot()
        with pytest.raises(RuntimeError):
            await s.loginSesame()

    @pytest.mark.asyncio
    async def test_CHSesameBot_lock_raises_exception_on_no_device_connenction(self):
        s = CHSesameBot()
        with pytest.raises(RuntimeError):
            await s.lock()

    @pytest.mark.asyncio
    async def test_CHSesameBot_click(self):
        s = CHSesameBot()
        s.setDeviceStatus(CHSesame2Status.Unlocked)

        assert (await s.click()) is None

    @pytest.mark.asyncio
    async def test_CHSesameBot_click_raises_exception_on_no_device_connenction(self):
        s = CHSesameBot()
        with pytest.raises(RuntimeError):
            await s.click()

    @pytest.mark.asyncio
    async def test_CHSesameBot_lock(self):
        s = CHSesameBot()
        s.setDeviceStatus(CHSesame2Status.Unlocked)

        assert (await s.lock()) is None

    @pytest.mark.asyncio
    async def test_CHSesameBot_unlock_raises_exception_on_no_device_connenction(self):
        s = CHSesameBot()
        with pytest.raises(RuntimeError):
            await s.unlock()

    @pytest.mark.asyncio
    async def test_CHSesameBot_unlock(self):
        s = CHSesameBot()
        s.setDeviceStatus(CHSesame2Status.Locked)

        assert (await s.unlock()) is None

    @pytest.mark.asyncio
    async def test_CHSesameBot_toggle_raises_exception_on_no_device_connenction(self):
        s = CHSesameBot()
        with pytest.raises(RuntimeError):
            await s.toggle()

    @pytest.mark.asyncio
    async def test_CHSesameBot_toggle_raises_exception_before_setMechStatus(self):
        s = CHSesameBot()
        s.setDeviceStatus(CHSesame2Status.Locked)
        with pytest.raises(RuntimeError):
            await s.toggle()

    @pytest.mark.asyncio
    async def test_CHSesameBot_toggle_to_unlocking(self):
        s = CHSesameBot()
        s.setDeviceStatus(CHSesame2Status.Locked)
        s.setMechStatus(CHSesameBotMechStatus(rawdata="5503000000000102"))

        with patch("pysesameos2.chsesamebot.CHSesameBot.unlock") as unlock:
            assert (await s.toggle()) is None
        unlock.assert_called_once()

    @pytest.mark.asyncio
    async def test_CHSesameBot_toggle_to_locking(self):
        s = CHSesameBot()
        s.setDeviceStatus(CHSesame2Status.Unlocked)
        s.setMechStatus(CHSesameBotMechStatus(rawdata="5503000000000104"))

        with patch("pysesameos2.chsesamebot.CHSesameBot.lock") as lock:
            assert (await s.toggle()) is None
        lock.assert_called_once()

    # TODO: Develop tests for the methods which relate to BleakClient.
