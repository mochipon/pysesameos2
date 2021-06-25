from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import bleak
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms

from pysesameos2.ble import (
    CHSesame2BleLoginResponse,
    CHSesame2BleNotify,
    CHSesame2BlePayload,
    CHSesame2BlePublish,
    CHSesame2BleReceiver,
    CHSesame2BleResponse,
    CHSesame2BleTransmiter,
)
from pysesameos2.const import (
    RX_UUID,
    SERVICE_UUID,
    TX_UUID,
    BleCmdResultCode,
    BleCommunicationType,
    BleItemCode,
    BleOpCode,
    CHDeviceLoginStatus,
    CHSesame2Intention,
    CHSesame2Status,
)
from pysesameos2.crypto import AppKeyFactory, BleCipher
from pysesameos2.device import CHSesameLock
from pysesameos2.helper import (
    CHSesame2MechSettings,
    CHSesame2MechStatus,
    HistoryTagHelper,
)

if TYPE_CHECKING:
    from bleak.backends.client import BaseBleakClient


logger = logging.getLogger(__name__)


class CHSesame2(CHSesameLock):
    def __init__(self) -> None:
        """SESAME3 Device Specific Implementation."""
        super().__init__()
        self._rxBuffer = CHSesame2BleReceiver()
        self._txBuffer = None
        self._mechStatus = None
        self._mechSetting = None
        self._intention = None

    def getRxBuffer(self) -> CHSesame2BleReceiver:
        return self._rxBuffer

    def setRxBuffer(self, ble_rx: CHSesame2BleReceiver):
        self._rxBuffer = ble_rx

    def getTxBuffer(self) -> CHSesame2BleTransmiter:
        return self._txBuffer

    def setTxBuffer(self, ble_tx: CHSesame2BleTransmiter):
        self._txBuffer = ble_tx

    def getMechStatus(self) -> CHSesame2MechStatus:
        """Return a mechanical status of a device.

        Returns:
            CHSesame2MechStatus: Current mechanical status of the device.
        """
        return self._mechStatus

    def setMechStatus(self, status: CHSesame2MechStatus) -> None:
        """Set a mechanincal status of a device.

        Args:
            status (CHSesame2MechStatus): Current mechanical status of the device.
        """
        if not isinstance(status, CHSesame2MechStatus):
            raise TypeError("Invalid status")

        logger.debug(f"setMechStatus: {str(status)}")
        self._mechStatus = status

        if status.getTarget() == -32768:
            self.setIntention(CHSesame2Intention.idle)
        else:
            setting = self.getMechSetting()

            if setting is None:
                self.setIntention(CHSesame2Intention.movingToUnknownTarget)
            elif status.getTarget() == setting.getLockPosition():
                self.setIntention(CHSesame2Intention.locking)
            elif status.getTarget() == setting.getUnlockPosition():
                self.setIntention(CHSesame2Intention.unlocking)

    def getMechSetting(self) -> CHSesame2MechSettings:
        """Return mechanical settings of a device

        Returns:
            CHSesame2MechSettings: The mechanical settings of the device
        """
        return self._mechSetting

    def setMechSetting(self, setting: CHSesame2MechSettings):
        """Set mechanical settings of a device

        Args:
            setting (CHSesame2MechSettings): The mechanical settings of the device
        """
        if not isinstance(setting, CHSesame2MechSettings):
            raise TypeError("Invalid setting")

        logger.debug(f"setMechSetting: {str(setting)}")
        self._mechSetting = setting

    def getIntention(self) -> CHSesame2Intention:
        """Return an inntenntion of a device

        Returns:
            CHSesame2Intention: The intention of the device
        """
        return self._intention

    def setIntention(self, intent: CHSesame2Intention) -> None:
        """Set an intention of a device

        Args:
            intent (CHSesame2Intention): The intention of the device
        """
        logger.debug(f"setIntention: {intent}")
        self._intention = intent

    async def connect(self):
        logger.debug("Connect to the device...")
        self._client = bleak.BleakClient(self.getAdvertisement().getDevice())
        self.setDeviceStatus(CHSesame2Status.BleConnecting)
        ret = await self._client.connect()
        if not ret:
            raise RuntimeError("Failed to connect the device.")
        self._client.set_disconnected_callback(self.onConnectionStateChange)

        logger.info(f"Connected to the device: {self.getDeviceUUID()}")
        self.setDeviceStatus(CHSesame2Status.WaitingGatt)
        services = await self._client.get_services()
        for s in services:
            if s.uuid == SERVICE_UUID:
                self.setCharacteristicTX(s.get_characteristic(TX_UUID))
                await self._client.start_notify(
                    s.get_characteristic(RX_UUID), self.onCharacteristicChanged
                )
                logger.debug("Found RX/TX characteristics.")

    async def disconnect(self):
        try:
            logger.info(f"Disconnecting from the device: {self.getDeviceUUID()}")
            self.setDeviceStatus(CHSesame2Status.NoBleSignal)
            await self._client.stop_notify(RX_UUID)
            await self._client.disconnect()
            logger.info(
                f"Successfully disconnected from the device: {self.getDeviceUUID()}"
            )
        except (ValueError, Exception):
            logger.exception(
                f"Error disconnecting to the device: {self.getDeviceUUID()}"
            )
            pass

    async def transmit(self) -> None:
        if self.getCharacteristicTX() is not None:
            c = self.getCharacteristicTX()

            tx_buffer = self.getTxBuffer()
            if tx_buffer is not None:
                chunk = tx_buffer.getChunk()
                while chunk is not None:
                    logger.debug(f"BLE Transmit: {c}")
                    await self._client.write_gatt_char(c, chunk, response=False)
                    chunk = tx_buffer.getChunk()
        else:
            raise RuntimeError(
                "Attempted to send data without completing the initial negotiation."
            )

    async def sendCommand(
        self, payload: CHSesame2BlePayload, is_cipher: BleCommunicationType
    ) -> None:
        if is_cipher == BleCommunicationType.ciphertext:
            cipher = self.getCipher()
            payload_full = (
                cipher.encrypt(payload.toDataWithHeader())
                if cipher is not None
                else None
            )
        else:
            payload_full = payload.toDataWithHeader()

        if payload_full is not None:
            logger.debug(
                f"sendCommand: UUID={self.getDeviceUUID()}, is_cipher={is_cipher}, OpCode={payload.getOpCode()}, ItCode={payload.getItCode()}"
            )
            self.setTxBuffer(CHSesame2BleTransmiter(is_cipher, payload_full))
            await self.transmit()

    async def loginSesame(self):
        logging.debug(f"Login to the device: {self.getDeviceUUID()}")
        self.setDeviceStatus(CHSesame2Status.BleLogining)

        remote_keys = self.getKey()
        local_keys = AppKeyFactory.get_instance()

        sesame_sk = remote_keys.getSecretKey()
        sesame_keyindex = remote_keys.getKeyIndex()
        sesame_pk = remote_keys.getSesame2PublicKey()
        local_pk = local_keys.getPubkey()

        tokens = local_keys.getAppToken() + self.getSesameToken()

        c = cmac.CMAC(algorithms.AES(sesame_sk))
        c.update(sesame_keyindex + local_pk + tokens)
        cmac_tag_response = c.finalize()[0:4]

        c = cmac.CMAC(algorithms.AES(local_keys.ecdh(sesame_pk)[0:16]))
        c.update(tokens)
        cmac_tag = c.finalize()

        self.setCipher(BleCipher(cmac_tag, tokens))
        payload = (
            sesame_keyindex + local_pk + local_keys.getAppToken() + cmac_tag_response
        )
        await self.sendCommand(
            CHSesame2BlePayload(BleOpCode.sync, BleItemCode.login, payload),
            BleCommunicationType.plaintext,
        )

    def onConnectionStateChange(self, _: BaseBleakClient):
        logger.debug("onConnectionStateChange")
        self.setAdvertisement(None)

    async def onCharacteristicChanged(self, _: int, data: bytearray) -> None:
        # The value passed to this callback is actually being casted to `bytearray`.
        # Here we explicitly re-cast it to `bytes` thereby the value should be immutable.
        segment_type, rawdata = self.getRxBuffer().feed(bytes(data))

        if rawdata is None:
            # Fragmented packet?
            logger.debug(
                "onCharacteristicChanged: the packet is a part of fragmented packets."
            )
            return

        # Decrypt if needed.
        if segment_type == BleCommunicationType.plaintext:
            notify_payload = CHSesame2BleNotify(rawdata)
        elif segment_type == BleCommunicationType.ciphertext:
            cipher = self.getCipher()
            notify_payload = CHSesame2BleNotify(cipher.decrypt(rawdata))

        if notify_payload.getNotifyOpCode() == BleOpCode.publish:
            publish_payload = CHSesame2BlePublish(notify_payload.getPayload())
            logger.debug(
                f"onCharacteristicChanged: Type=Notify, OpCode=Publish, CmdItCode={publish_payload.getCmdItCode()}"
            )
            await self.onGattSesamePublish(publish_payload)

        if notify_payload.getNotifyOpCode() == BleOpCode.response:
            response_payload = CHSesame2BleResponse(notify_payload.getPayload())
            logger.debug(
                f"onCharacteristicChanged: Type=Notify, OpCode=Response, CmdItCode={response_payload.getCmdItCode()}, CmdOPCode={response_payload.getCmdOPCode()}, CmdResultCode={response_payload.getCmdResultCode()}"
            )

            if (
                response_payload.getCmdItCode() == BleItemCode.login
                and response_payload.getCmdResultCode() == BleCmdResultCode.success
            ):
                login_response = CHSesame2BleLoginResponse(
                    response_payload.getPayload()
                )

                logger.debug(
                    f"onCharacteristicChanged: retrived {str(login_response.getMechSetting())}"
                )
                self.setMechSetting(login_response.getMechSetting())
                logger.debug(
                    f"onCharacteristicChanged: retrived {str(login_response.getMechStatus())}"
                )
                self.setMechStatus(login_response.getMechStatus())
                if self.getMechSetting().isConfigured:
                    self.setDeviceStatus(
                        CHSesame2Status.Locked
                        if self.getMechStatus().isInLockRange()
                        else CHSesame2Status.Unlocked
                    )
                else:
                    self.setDeviceStatus(CHSesame2Status.NoSettings)

    async def onGattSesamePublish(self, publish_payload: CHSesame2BlePublish) -> None:
        if publish_payload.getCmdItCode() == BleItemCode.initial:
            logger.debug(
                f"onGattSesamePublish: recieved token={publish_payload.getPayload().hex()}"
            )
            self.setSesameToken(publish_payload.getPayload())

            if not self.getRegistered():
                self.setDeviceStatus(CHSesame2Status.ReadyToRegister)
                raise ValueError(
                    "This SESAME3 is not supported: initial configuration needed."
                )
            else:
                await self.loginSesame()

        if publish_payload.getCmdItCode() == BleItemCode.mechStatus:
            logger.debug(
                f"onGattSesamePublish: recieved {str(CHSesame2MechStatus(rawdata=publish_payload.getPayload()))}"
            )
            self.setMechStatus(
                CHSesame2MechStatus(rawdata=publish_payload.getPayload())
            )
            self.setDeviceStatus(
                CHSesame2Status.Locked
                if self.getMechStatus().isInLockRange()
                else CHSesame2Status.Unlocked
            )

        if publish_payload.getCmdItCode() == BleItemCode.mechSetting:
            logger.debug(
                f"onGattSesamePublish: recieved {str(CHSesame2MechSettings(rawdata=publish_payload.getPayload()))}"
            )
            self.setMechSetting(
                CHSesame2MechSettings(rawdata=publish_payload.getPayload())
            )
            self.setDeviceStatus(
                CHSesame2Status.Locked
                if self.getMechStatus().isInLockRange()
                else CHSesame2Status.Unlocked
            )

    async def lock(self, history_tag: str = "pysesameos2") -> None:
        """Locking.

        Args:
            history_tag (str): The key tag to sent when locking and unlocking. Defaults to `pysesameos2`.
        """
        if self.getDeviceStatus().value == CHDeviceLoginStatus.UnLogin:
            raise RuntimeError("No device connenction.")

        logger.info(f"Lock: UUID={self.getDeviceUUID()}, history_tag={history_tag}")
        await self.sendCommand(
            CHSesame2BlePayload(
                BleOpCode.async_,
                BleItemCode.lock,
                HistoryTagHelper.create_htag(history_tag),
            ),
            BleCommunicationType.ciphertext,
        )

    async def unlock(self, history_tag: str = "pysesameos2") -> None:
        """Unlocking.

        Args:
            history_tag (str): The key tag to sent when locking and unlocking. Defaults to `pysesameos2`.
        """
        if self.getDeviceStatus().value == CHDeviceLoginStatus.UnLogin:
            raise RuntimeError("No device connenction.")

        logger.info(f"Unlock: UUID={self.getDeviceUUID()}, history_tag={history_tag}")
        await self.sendCommand(
            CHSesame2BlePayload(
                BleOpCode.async_,
                BleItemCode.unlock,
                HistoryTagHelper.create_htag(history_tag),
            ),
            BleCommunicationType.ciphertext,
        )

    def toggle(self, history_tag: str = "pysesameos2") -> None:
        """Toggle.

        Args:
            history_tag (str): The key tag to sent when locking and unlocking. Defaults to `pysesameos2`.
        """
        if self.getDeviceStatus().value == CHDeviceLoginStatus.UnLogin:
            raise RuntimeError("No device connenction.")

        status = self.getMechStatus()
        if status is None:
            raise RuntimeError("Current status is unknown")
        elif status.isInLockRange():
            return self.unlock(history_tag=history_tag)
        elif status.isInUnlockRange():
            return self.lock(history_tag=history_tag)

    def __str__(self) -> str:
        """Return a string representation of an object.

        Returns:
            str: The string representation of the object.
        """
        return f"CHSesame2(deviceUUID={self.getDeviceUUID()}, deviceModel={self.productModel}, sesame2PublicKey={self.getSesame2PublicKey()}, mechStatus={self.getMechStatus()})"
