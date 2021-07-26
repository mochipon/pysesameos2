import asyncio
import base64
import logging
import uuid
from typing import Dict, Optional, Tuple, Union

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from pysesameos2.const import (
    SERVICE_UUID,
    BleCmdResultCode,
    BleCommunicationType,
    BleItemCode,
    BleOpCode,
    BlePacketType,
)
from pysesameos2.device import CHDevices
from pysesameos2.helper import CHProductModel

logger = logging.getLogger(__name__)


class CHSesame2BleTransmiter:
    def __init__(self, segment_type: BleCommunicationType, data: bytes) -> None:
        """An object responsible for sending data using BLE.

        Args:
            segment_type (BleCommunicationType): Specify whether the data should be encrypted or not.
            data (bytes): The rawdata to be sent.
        """
        if not isinstance(segment_type, BleCommunicationType):
            raise TypeError("Invalid segment_type")
        if not isinstance(data, bytes):
            raise TypeError("Invalid data")

        self._mtu = 19
        self._input = data
        self._BleCommunicationType = segment_type
        self._isStartFirstCut = True

        self._waitsend = [
            data[i : i + self._mtu] for i in range(0, len(data), self._mtu)
        ]
        logger.debug(
            "The packet is fragmented into {} packets.".format(len(self._waitsend))
        )

    def getChunk(self) -> Optional[bytes]:
        """Return a chunk of packet to be sent.

        Returns:
            bytes: The data can be transmitted (MTU size-aware)
        """
        if self._isStartFirstCut:
            header = bytes(
                [
                    BlePacketType.isStart.value
                    | (
                        (
                            self._BleCommunicationType.value
                            if len(self._waitsend) == 1
                            else BlePacketType.APPEND_ONLY.value
                        )
                        << 1
                    )
                ]
            )
            self._isStartFirstCut = False
            logger.debug(f"getChunk: This is the first packet, header={header.hex()}")
            return header + self._waitsend[0]
        else:
            f = self._waitsend[1:]
            self._waitsend = f
            if len(f) == 0:
                return None

            header = bytes(
                [
                    BlePacketType.NotStart.value
                    | (
                        (
                            self._BleCommunicationType.value
                            if len(self._waitsend) == 1
                            else BlePacketType.APPEND_ONLY.value
                        )
                        << 1
                    )
                ]
            )
            logger.debug(
                f"getChunk: This is not a first packet, header={header.hex()}, left={len(self._waitsend)} pkts"
            )
            return header + self._waitsend[0]


class CHSesame2BleReceiver:
    def __init__(self) -> None:
        """An object responsible for rerceiving data using BLE.

        The most important role is to merge the fragmented packets.
        """
        self.buffer = bytearray()

    def feed(
        self, barr: bytes
    ) -> Union[Tuple[BleCommunicationType, bytes], Tuple[None, None]]:
        """Handle a received packet.

        Args:
            barr (bytes): The received rawdata.

        Returns:
            Union[Tuple[BleCommunicationType, bytes], Tuple[None, None]]: [description]
        """
        b = barr[0]
        i = b & 1
        i2 = b >> 1

        if i > 0:
            self.buffer = bytearray(barr[1:])
        else:
            logger.debug("feed: This is the last fragmented packet.")
            self.buffer += barr[1:]

        if i2 == 0:
            logger.debug("feed: This is a part of fragmented packet.")
            return (None, None)

        return (BleCommunicationType(i2), bytes(self.buffer))


class CHSesame2BlePayload:
    def __init__(self, op_code: BleOpCode, item_code: BleItemCode, data: bytes) -> None:
        """Represents a payload of a packet to be sent.

        Args:
            op_code (BleOpCode): The desired operation.
            item_code (BleItemCode): The item to be operated.
            data (bytes): The rawdata.
        """
        if not isinstance(op_code, BleOpCode):
            raise TypeError("Invalid op_code")
        if not isinstance(item_code, BleItemCode):
            raise TypeError("Invalid item_code")
        if not isinstance(data, bytes):
            raise TypeError("Invalid data")

        self._op_code = op_code
        self._item_code = item_code
        self._data = data

    def getOpCode(self) -> BleOpCode:
        """Return an executed operation code.

        Returns:
            BleItemCode: The operation code.
        """
        return self._op_code

    def getItCode(self) -> BleItemCode:
        """Return an operated item code.

        Returns:
            BleItemCode: The item code.
        """
        return self._item_code

    def toDataWithHeader(self) -> bytes:
        """Return a data including a header.

        Returns:
            bytes: The rawdata to be sent.
        """
        return bytes([self._op_code.value, self._item_code.value]) + self._data


class CHSesame2BleNotify:
    def __init__(self, data: bytes) -> None:
        """A representation of a notification from a device.

        Args:
            data (bytes): The rawdata.
        """
        if not isinstance(data, bytes):
            raise TypeError("Invalid data")

        self._data = data
        self._notifyOpCode = BleOpCode(int(data[0]))
        self._payload = data[1:]

    def getNotifyOpCode(self) -> BleOpCode:
        """Return an operation code.

        Returns:
            BleItemCode: The operation code.
        """
        return self._notifyOpCode

    def getPayload(self) -> bytes:
        """Return a payload of a packet.

        Returns:
            bytes: The payload.
        """
        return self._payload


class CHSesame2BlePublish:
    def __init__(self, data: bytes) -> None:
        """A representation of a publish packet.

        Args:
            data (bytes): The rawdata.
        """
        if not isinstance(data, bytes):
            raise TypeError("Invalid data")

        self._data = data
        self._cmdItCode = BleItemCode(int(data[0]))
        self._payload = data[1:]

    def getCmdItCode(self) -> BleItemCode:
        """Return an operated item code.

        Returns:
            BleItemCode: The item code.
        """
        return self._cmdItCode

    def getPayload(self) -> bytes:
        """Return a payload of a packet.

        Returns:
            bytes: The payload.
        """
        return self._payload


class CHSesame2BleResponse:
    def __init__(self, data: bytes) -> None:
        """A representation of a response packet.

        Args:
            data (bytes): The rawdata.
        """
        if not isinstance(data, bytes):
            raise TypeError("Invalid data")

        self._data = data
        self._cmdItCode = BleItemCode(int(data[0]))
        self._cmdOPCode = BleOpCode(int(data[1]))
        self._cmdResultCode = BleCmdResultCode(int(data[2]))
        self._payload = data[3:]

    def getCmdItCode(self) -> BleItemCode:
        """Return an operated item code.

        Returns:
            BleItemCode: The item code.
        """
        return self._cmdItCode

    def getCmdOPCode(self) -> BleOpCode:
        """Return an executed operation code.

        Returns:
            BleItemCode: The operation code.
        """
        return self._cmdOPCode

    def getCmdResultCode(self) -> BleCmdResultCode:
        """Return a result code of an operation.

        Returns:
            BleCmdResultCode: The result code.
        """
        return self._cmdResultCode

    def getPayload(self) -> bytes:
        """Return a payload of a packet.

        Returns:
            bytes: The payload.
        """
        return self._payload


class BLEAdvertisement:
    def __init__(self, dev: BLEDevice, manufacturer_data: dict) -> None:
        if not isinstance(dev, BLEDevice):
            raise TypeError("Invalid dev")
        if not isinstance(manufacturer_data, dict):
            raise TypeError("Invalid manufacturer_data")

        self._address = dev.address
        self._device = dev
        self._rssi = dev.rssi

        self._advBytes = next(iter(manufacturer_data.values()))
        self._productModel = CHProductModel.getByValue(self._advBytes[0])
        self._isRegistered = (self._advBytes[2] & 1) > 0

        if self._productModel == CHProductModel.WM2:
            self._deviceId = uuid.UUID(
                "00000000055afd810001" + self._advBytes[3:9].hex()
            )
        else:
            self._deviceId = uuid.UUID(
                bytes=base64.b64decode("{}==".format(dev.name).encode("utf-8"))
            )

    def getAddress(self) -> str:
        return self._address

    def getDevice(self) -> BLEDevice:
        return self._device

    def getRssi(self) -> int:
        return self._rssi

    def getDeviceID(self) -> uuid.UUID:
        return self._deviceId

    def getProductModel(self) -> CHProductModel:
        return self._productModel

    def isRegistered(self) -> bool:
        return self._isRegistered


class CHBleManager:
    def device_factory(self, dev: BLEDevice) -> CHDevices:
        """Return a device object corresponding to a BLE advertisement.

        Args:
            dev (BLEDevice): The discovered BLE device.

        Returns:
            CHDevices: The candyhouse device.
        """
        if not isinstance(dev, BLEDevice):
            raise TypeError("Invalid dev")

        if dev.name is None:
            raise ValueError("Failed to find the device name")

        # `BLEDevice.metadata` should return device specific details in OS-agnostically way.
        # https://bleak.readthedocs.io/en/latest/api.html#bleak.backends.device.BLEDevice.metadata
        if (
            dev.metadata is None
            or "uuids" not in dev.metadata
            or "manufacturer_data" not in dev.metadata
        ):
            raise ValueError("Failed to find the device metadata")

        if SERVICE_UUID in dev.metadata["uuids"]:
            adv = BLEAdvertisement(dev, dev.metadata["manufacturer_data"])
            device = adv.getProductModel().deviceFactory()()
            device.setAdvertisement(adv)

            return device
        else:
            raise ValueError("Failed to find the service uuid")

    async def scan(self, scan_duration: int = 10) -> Dict[str, CHDevices]:
        """Scan devices.

        Args:
            scan_duration (int): Keeping the scaninng time (Unit: second).

        Returns:
            Dict[str, CHDevices]: Devices discovered.
        """
        logger.info("Starting scan for SESAME devices...")
        ret = {}
        try:
            devices = await asyncio.wait_for(BleakScanner.discover(), scan_duration)

            for device in devices:
                try:
                    obj = self.device_factory(device)
                except NotImplementedError:
                    logger.warning("Unsupported SESAME device is found, skip.")
                    continue
                except ValueError:
                    logger.warning("Not a SESAME device, skip.")
                    continue

                if obj is not None:
                    ret[device.address] = obj
        except BleakError as e:
            logger.exception(e)

        logger.info("Scan completed: found {} devices".format(len(ret)))
        return ret

    async def scan_by_address(
        self, ble_device_identifier: str, scan_duration: int = 10
    ) -> CHDevices:
        """Scan a device by its Bluetooth/UUID address.

        Args:
            ble_device_identifier (str): The Bluetooth/UUID address for specified scanninng.
            scan_duration (int): Keeping the scaninng time (Unit: second).

        Returns:
            CHDevices: Devices discovered.
        """
        logger.info(
            "Starting scan for the SESAME device ({})...".format(ble_device_identifier)
        )

        # We do use `BleakScanner.discover` instead of
        # `BleakScanner.find_device_by_address`.
        #
        # The problem is, the reposence (`BLEDevice`) of `find_device_by_address` does not
        # contain a proper `matadata` which is heavily utilized in `device_factory`.
        #
        # `discover` internally calls `discovered_devices` which provides
        # OS-agnostic `metadata` of the device.
        # https://github.com/hbldh/bleak/blob/55a2d34cc96bb842be278485794806704caa2d2c/bleak/backends/scanner.py#L101
        # https://github.com/hbldh/bleak/blob/ce63ed4d92430f154ce33ab812e313961b26f7a4/bleak/backends/bluezdbus/scanner.py#L213-L237

        devices = await asyncio.wait_for(BleakScanner.discover(), scan_duration)

        device = next(
            (d for d in devices if d.address.lower() == ble_device_identifier.lower()),
            None,
        )
        if device is None:
            raise ConnectionRefusedError("Scan completed: the device not found")

        try:
            obj = self.device_factory(device)
        except NotImplementedError:
            raise NotImplementedError("This device is not supported.")
        except ValueError:
            raise ValueError("This is not a SESAME device.")

        obj = self.device_factory(device)

        logger.info("Scan completed: found the device")
        return obj
