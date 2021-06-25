#!/usr/bin/env python

"""Tests for `pysesameos2` package."""

import bleak
import pytest

from pysesameos2.ble import CHBleManager, CHSesame2BleReceiver, CHSesame2BleTransmiter
from pysesameos2.chsesame2 import CHSesame2
from pysesameos2.const import BleCommunicationType, CHSesame2Intention
from pysesameos2.helper import CHSesame2MechSettings, CHSesame2MechStatus


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

    # TODO: Develop tests for the methods which relate to BleakClient.
