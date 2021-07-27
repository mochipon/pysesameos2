#!/usr/bin/env python

"""Tests for `pysesameos2` package."""

import sys
import uuid

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from pysesameos2.ble import (
    BLEAdvertisement,
    CHBleManager,
    CHSesame2BleNotify,
    CHSesame2BlePayload,
    CHSesame2BlePublish,
    CHSesame2BleReceiver,
    CHSesame2BleResponse,
    CHSesame2BleTransmiter,
)
from pysesameos2.chsesame2 import CHSesame2
from pysesameos2.const import (
    BleCmdResultCode,
    BleCommunicationType,
    BleItemCode,
    BleOpCode,
)
from pysesameos2.helper import (
    CHProductModel,
    CHSesame2MechSettings,
    CHSesame2MechStatus,
)

if sys.version_info[:2] < (3, 8):
    from asynctest import patch
else:
    from unittest.mock import patch


@pytest.fixture
def bleak_scanner():
    with patch("pysesameos2.ble.BleakScanner") as scanner:
        yield scanner


class TestCHSesame2BleTransmiter:
    def test_CHSesame2BleTransmiter_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleTransmiter()

        with pytest.raises(TypeError):
            CHSesame2BleTransmiter(BleCommunicationType.plaintext)

    def test_CHSesame2BleTransmiter_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleTransmiter("INVALID", bytes([0]))

        with pytest.raises(TypeError):
            CHSesame2BleTransmiter(BleCommunicationType.plaintext, "INVALID")

    def test_CHSesame2BleTransmiter(self):
        segment_type = BleCommunicationType.plaintext
        data = bytes.fromhex("feedfeedfeedfeedfeedfeedfeedfeed")
        assert CHSesame2BleTransmiter(segment_type, data)

    def test_CHSesame2BleTransmiter_getChunk(self):
        segment_type = BleCommunicationType.plaintext
        data = bytes.fromhex("feed" * 20)
        t = CHSesame2BleTransmiter(segment_type, data)

        first_chunk = bytes.fromhex("01" + "feed" * 9 + "fe")
        second_chunk = bytes.fromhex("00ed" + "feed" * 9)
        third_chunk = bytes.fromhex("02feed")

        assert len(first_chunk) == 20
        assert len(second_chunk) == 20

        assert t.getChunk() == first_chunk
        assert t.getChunk() == second_chunk
        assert t.getChunk() == third_chunk
        assert t.getChunk() is None


class TestCHSesame2BleReceiver:
    def test_CHSesame2BleReceiver_feed(self):
        r = CHSesame2BleReceiver()

        first_chunk = bytes.fromhex("01" + "feed" * 9 + "fe")
        second_chunk = bytes.fromhex("00ed" + "feed" * 9)
        third_chunk = bytes.fromhex("02feed")

        assert r.feed(first_chunk) == (None, None)
        assert r.feed(second_chunk) == (None, None)
        assert r.feed(third_chunk) == (
            BleCommunicationType.plaintext,
            bytes.fromhex("feed" * 20),
        )


class TestCHSesame2BlePayload:
    def test_CHSesame2BlePayload_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BlePayload()

    def test_CHSesame2BlePayload_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BlePayload("INVALID", BleItemCode.initial, bytes([0]))

        with pytest.raises(TypeError):
            CHSesame2BlePayload(BleOpCode.read, "INVALID", bytes([0]))

        with pytest.raises(TypeError):
            CHSesame2BlePayload(BleOpCode.read, BleItemCode.initial, "INVALID")

    def test_CHSesame2BlePayload(self):
        p = CHSesame2BlePayload(BleOpCode.read, BleItemCode.history, bytes([1]))

        assert p.getOpCode() == BleOpCode.read
        assert p.getItCode() == BleItemCode.history
        assert p.toDataWithHeader() == bytes.fromhex("020401")


class TestCHSesame2BleNotify:
    def test_CHSesame2BleNotify_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleNotify()

    def test_CHSesame2BleNotify_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleNotify("INVALID-DATA")

    def test_CHSesame2BleNotify(self):
        n = CHSesame2BleNotify(bytes.fromhex("07040205"))

        assert n.getNotifyOpCode() == BleOpCode.response
        assert n.getPayload() == bytes.fromhex("040205")


class TestCHSesame2BlePublish:
    def test_CHSesame2BlePublish_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BlePublish()

    def test_CHSesame2BlePublish_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BlePublish("INVALID-DATA")

    def test_CHSesame2BlePublish(self):
        p = CHSesame2BlePublish(bytes.fromhex("515d030080e6010002"))

        assert p.getCmdItCode() == BleItemCode.mechStatus
        assert p.getPayload() == bytes.fromhex("5d030080e6010002")


class TestCHSesame2BleResponse:
    def test_CHSesame2BleResponse_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleResponse()

    def test_CHSesame2BleResponse_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHSesame2BleResponse("INVALID-DATA")

    def test_CHSesame2BleResponse(self):
        r = CHSesame2BleResponse(bytes.fromhex("040205"))

        assert r.getCmdItCode() == BleItemCode.history
        assert r.getCmdOPCode() == BleOpCode.read
        assert r.getCmdResultCode() == BleCmdResultCode.notFound
        assert r.getPayload() == bytes(0)


class TestBLEAdvertisement:
    def test_BLEAdvertisement_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            BLEAdvertisement()

        with pytest.raises(TypeError):
            BLEAdvertisement(BLEDevice("AA:BB:CC:11:22:33", "QpGK0YFUSv+9H/DN6IqN4Q"))

    def test_BLEAdvertisement_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            BLEAdvertisement("INVALID-DATA", {1370: b"\x00\x00\x01"})

        with pytest.raises(TypeError):
            BLEAdvertisement(
                BLEDevice("AA:BB:CC:11:22:33", "QpGK0YFUSv+9H/DN6IqN4Q"),
                "INVALID",
            )

    def test_BLEAdvertisement(self):
        d = BLEDevice(
            "AA:BB:CC:11:22:33",
            "QpGK0YFUSv+9H/DN6IqN4Q",
            uuids=[
                "0000fd81-0000-1000-8000-00805f9b34fb",
            ],
            rssi=-60,
            manufacturer_data={1370: b"\x00\x00\x01"},
        )
        b = BLEAdvertisement(dev=d, manufacturer_data={1370: b"\x00\x00\x01"})

        assert b.getAddress() == "AA:BB:CC:11:22:33"
        assert b.getDevice() == d
        assert b.getRssi() == -60
        assert b.getDeviceID() == uuid.UUID("42918ad1-8154-4aff-bd1f-f0cde88a8de1")
        assert b.getProductModel() == CHProductModel.SS2
        assert b.isRegistered()


class TestCHBleManager:
    def test_CHBleManager_device_factory_raises_exception_on_missing_arguments(self):
        with pytest.raises(TypeError):
            CHBleManager().device_factory()

    def test_CHBleManager_device_factory_raises_exception_on_invalid_arguments(self):
        with pytest.raises(TypeError):
            CHBleManager().device_factory("INVALID-DATA")

    def test_CHBleManager_device_factory_not_supported_device(self):
        bled = BLEDevice(
            "AA:BB:CC:11:22:33",
            "QpGK0YFUSv+9H/DN6IqN4Q",
            uuids=[
                "0000fd81-0000-1000-8000-00805f9b34fb",
            ],
            rssi=-60,
            manufacturer_data={1370: b"\xff\x00\x01"},
        )

        with pytest.raises(NotImplementedError):
            assert CHBleManager().device_factory(bled)

    def test_CHBleManager_device_factory(self):
        bled = BLEDevice(
            "AA:BB:CC:11:22:33",
            "QpGK0YFUSv+9H/DN6IqN4Q",
            uuids=[
                "0000fd81-0000-1000-8000-00805f9b34fb",
            ],
            rssi=-60,
            manufacturer_data={1370: b"\x00\x00\x01"},
        )

        d = CHBleManager().device_factory(bled)
        assert isinstance(d, CHSesame2)

    @pytest.mark.asyncio
    async def test_CHBleManager_scan_returns_None(self, bleak_scanner):
        async def _scan(*args, **kwargs):
            """Simulate a scanning response"""
            return [
                BLEDevice(
                    "AA:BB:CC:11:22:33",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\xff\x00\x01"},
                ),
                BLEDevice(
                    "AA:BB:CC:44:55:66",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    uuids=[
                        "ffffffff-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\x00\x00\x01"},
                ),
            ]

        bleak_scanner.discover.side_effect = _scan

        assert await CHBleManager().scan() == {}

        bleak_scanner.discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_CHBleManager_scan_pass_BleakError_exception(self, bleak_scanner):
        async def raise_exception(*args, **kwargs):
            raise BleakError("TEST")

        bleak_scanner.discover.side_effect = raise_exception

        devices = await CHBleManager().scan()
        assert len(devices) == 0

        bleak_scanner.discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_CHBleManager_scan(self, bleak_scanner):
        async def _scan(*args, **kwargs):
            """Simulate a scanning response"""
            return [
                BLEDevice(
                    "AA:BB:CC:11:22:33",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\x00\x00\x01"},
                ),
                BLEDevice(
                    "AA:BB:CC:44:55:66",
                    "Em09ZpIiTlq83gxmKdSNQw",
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-70,
                    manufacturer_data={1370: b"\x00\x00\x01"},
                ),
            ]

        bleak_scanner.discover.side_effect = _scan

        devices = await CHBleManager().scan()

        assert len(devices) == 2
        assert "AA:BB:CC:11:22:33" in devices
        assert "AA:BB:CC:44:55:66" in devices

        bleak_scanner.discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_CHBleManager_scan_by_address_raises_exception_on_device_missing(
        self, bleak_scanner
    ):
        async def _scan(*args, **kwargs):
            """Simulate a scanning response"""
            return []

        bleak_scanner.discover.side_effect = _scan

        with pytest.raises(ConnectionRefusedError):
            await CHBleManager().scan_by_address("AA:BB:CC:11:22:33")

        bleak_scanner.discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_CHBleManager_scan_by_address_raises_exception_on_broken_advertisement(
        self, bleak_scanner
    ):
        async def _scan(*args, **kwargs):
            """Simulate a scanning response"""
            return [
                BLEDevice(
                    "AA:BB:CC:11:22:33",
                    "INVALID_NAME",
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\x00\x00\x01"},
                ),
                BLEDevice(
                    "AA:BB:CC:44:55:66",
                    None,
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\x00\x00\x01"},
                ),
                BLEDevice(
                    "AA:BB:CC:77:88:99",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                ),
                BLEDevice(
                    "AA:BB:CC:AA:BB:CC",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    rssi=-60,
                    manufacturer_data={1370: b"\x02\x00\x01"},
                ),
                BLEDevice(
                    "AA:BB:CC:DD:EE:FF",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    uuids=[
                        "ffffffff-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\x02\x00\x01"},
                ),
            ]

        bleak_scanner.discover.side_effect = _scan

        with pytest.raises(ValueError):
            await CHBleManager().scan_by_address("AA:BB:CC:11:22:33")

        with pytest.raises(ValueError):
            await CHBleManager().scan_by_address("AA:BB:CC:44:55:66")

        with pytest.raises(ValueError):
            await CHBleManager().scan_by_address("AA:BB:CC:77:88:99")

        with pytest.raises(ValueError):
            await CHBleManager().scan_by_address("AA:BB:CC:AA:BB:CC")

        with pytest.raises(ValueError):
            await CHBleManager().scan_by_address("AA:BB:CC:DD:EE:FF")

        assert bleak_scanner.discover.call_count == 5

    @pytest.mark.asyncio
    async def test_CHBleManager_scan_by_address_raises_exception_for_non_supported_device(
        self, bleak_scanner
    ):
        async def _scan(*args, **kwargs):
            """Simulate a scanning response"""
            return [
                BLEDevice(
                    "AA:BB:CC:11:22:33",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\xff\x00\x01"},
                )
            ]

        bleak_scanner.discover.side_effect = _scan

        with pytest.raises(NotImplementedError):
            await CHBleManager().scan_by_address("AA:BB:CC:11:22:33")

        bleak_scanner.discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_CHBleManager_scan_by_address(self, bleak_scanner):
        async def _scan(*args, **kwargs):
            """Simulate a scanning response"""
            return [
                BLEDevice(
                    "AA:BB:CC:11:22:33",
                    "QpGK0YFUSv+9H/DN6IqN4Q",
                    uuids=[
                        "0000fd81-0000-1000-8000-00805f9b34fb",
                    ],
                    rssi=-60,
                    manufacturer_data={1370: b"\x00\x00\x01"},
                )
            ]

        bleak_scanner.discover.side_effect = _scan

        device = await CHBleManager().scan_by_address("AA:BB:CC:11:22:33")
        assert isinstance(device, CHSesame2)

        bleak_scanner.discover.assert_called_once()
