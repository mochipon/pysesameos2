import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bleak import BleakClient
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms

from pysesameos2.ble import (
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
    CHProductModel,
    CHSesameBotMechSettings,
    CHSesameBotMechStatus,
    HistoryTagHelper,
)

if TYPE_CHECKING:
    from bleak.backends.client import BaseBleakClient


logger = logging.getLogger(__name__)


class CHSesameBotBleLoginResponse:
    def __init__(self, data: bytes) -> None:
        """A representation of a response for login operation.

        Args:
            data (bytes): The rawdata.
        """
        if not isinstance(data, bytes):
            raise TypeError("Invalid data")

        self._systemTime = datetime.fromtimestamp(int.from_bytes(data[0:4], "little"))
        # ??? data[4:8]
        logger.info("mechSetting: {}".format(data[8:20].hex()))
        self._SSM2MechSetting = CHSesameBotMechSettings(rawdata=data[8:20])
        self._SSM2MechStatus = CHSesameBotMechStatus(rawdata=data[20:28])

    def getMechSetting(self) -> CHSesameBotMechSettings:
        """Return a mechanical setting of a device.

        Returns:
            CHSesameBotMechSettings: The mechanical settinng.
        """
        return self._SSM2MechSetting

    def getMechStatus(self) -> CHSesameBotMechStatus:
        """Return a mechanical status of a device.

        Returns:
            CHSesameBotMechStatus: The mechanical status.
        """
        return self._SSM2MechStatus


class CHSesameBot(CHSesameLock):
    def __init__(self) -> None:
        """SESAME bot Device Specific Implementation."""
        super().__init__()
        self._rxBuffer = CHSesame2BleReceiver()
        self._txBuffer: Optional[CHSesame2BleTransmiter] = None
        self._mechStatus: Optional[CHSesameBotMechStatus] = None
        self._mechSetting: Optional[CHSesameBotMechSettings] = None
        self._intention = CHSesame2Intention.idle

    def getRxBuffer(self) -> CHSesame2BleReceiver:
        return self._rxBuffer

    def setRxBuffer(self, ble_rx: CHSesame2BleReceiver) -> None:
        self._rxBuffer = ble_rx

    def getTxBuffer(self) -> Optional[CHSesame2BleTransmiter]:
        return self._txBuffer

    def setTxBuffer(self, ble_tx: CHSesame2BleTransmiter) -> None:
        self._txBuffer = ble_tx

    def getMechStatus(self) -> Optional[CHSesameBotMechStatus]:
        """Return a mechanical status of a device.

        Returns:
            CHSesameBotMechStatus: Current mechanical status of the device.
        """
        return self._mechStatus

    def setMechStatus(self, status: CHSesameBotMechStatus) -> None:
        """Set a mechanincal status of a device.

        Args:
            status (CHSesameBotMechStatus): Current mechanical status of the device.
        """
        if not isinstance(status, CHSesameBotMechStatus):
            raise TypeError("Invalid status")

        logger.debug(f"setMechStatus: {str(status)}")
        self._mechStatus = status

        if status.getMotorStatus() == 0:
            self.setIntention(CHSesame2Intention.idle)
        elif status.getMotorStatus() == 1:
            self.setIntention(CHSesame2Intention.locking)
        elif status.getMotorStatus() == 2:
            self.setIntention(CHSesame2Intention.holding)
        elif status.getMotorStatus() == 3:
            self.setIntention(CHSesame2Intention.unlocking)
        else:
            self.setIntention(CHSesame2Intention.movingToUnknownTarget)

    def getMechSetting(self) -> Optional[CHSesameBotMechSettings]:
        """Return mechanical settings of a device

        Returns:
            CHSesameBotMechSettings: The mechanical settings of the device
        """
        return self._mechSetting

    def setMechSetting(self, setting: CHSesameBotMechSettings) -> None:
        """Set mechanical settings of a device

        Args:
            setting (CHSesameBotMechSettings): The mechanical settings of the device
        """
        if not isinstance(setting, CHSesameBotMechSettings):
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

    async def connect(self) -> None:
        adv = self.getAdvertisement()
        if not adv:
            raise RuntimeError("BLE advertisement from the device is not received.")

        logger.debug("Connect to the device...")
        self._client = BleakClient(adv.getDevice())
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

    async def disconnect(self) -> None:
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

    async def loginSesame(self) -> None:
        logging.debug(f"Login to the device: {self.getDeviceUUID()}")

        remote_keys = self.getKey()
        sesame_sk = remote_keys.getSecretKey()
        sesame_keyindex = remote_keys.getKeyIndex()
        sesame_pk = remote_keys.getSesame2PublicKey()
        sesame_token = self.getSesameToken()
        if not sesame_sk or not sesame_keyindex or not sesame_pk or not sesame_token:
            raise RuntimeError("Missing parameters from the device for login process.")

        local_keys = AppKeyFactory.get_instance()
        local_pk = local_keys.getPubkey()
        local_token = local_keys.getAppToken()

        tokens = local_token + sesame_token

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

        self.setDeviceStatus(CHSesame2Status.BleLogining)
        await self.sendCommand(
            CHSesame2BlePayload(BleOpCode.sync, BleItemCode.login, payload),
            BleCommunicationType.plaintext,
        )

    def onConnectionStateChange(self, _: "BaseBleakClient") -> None:
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
            if cipher is None:
                raise RuntimeError("setCipher should be called before decryption.")
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
                login_response = CHSesameBotBleLoginResponse(
                    response_payload.getPayload()
                )
                mech_setting = login_response.getMechSetting()
                mech_status = login_response.getMechStatus()

                logger.debug(f"onCharacteristicChanged: retrived {str(mech_setting)}")
                self.setMechSetting(mech_setting)
                logger.debug(f"onCharacteristicChanged: retrived {str(mech_status)}")
                self.setMechStatus(mech_status)
                self.setDeviceStatus(
                    CHSesame2Status.Locked
                    if mech_status.isInLockRange()
                    else CHSesame2Status.Unlocked
                )

    async def onGattSesamePublish(self, publish_payload: CHSesame2BlePublish) -> None:
        if publish_payload.getCmdItCode() == BleItemCode.initial:
            logger.debug(
                f"onGattSesamePublish: recieved token={publish_payload.getPayload().hex()}"
            )
            self.setSesameToken(publish_payload.getPayload())

            if not self.getRegistered():
                self.setDeviceStatus(CHSesame2Status.ReadyToRegister)
                raise NotImplementedError(
                    "This SESAME3 is not supported: initial configuration needed."
                )
            else:
                await self.loginSesame()
        elif publish_payload.getCmdItCode() == BleItemCode.mechStatus:
            received_mechstatus = CHSesameBotMechStatus(
                rawdata=publish_payload.getPayload()
            )

            logger.debug(f"onGattSesamePublish: recieved {str(received_mechstatus)}")
            self.setMechStatus(received_mechstatus)
            self.setDeviceStatus(
                CHSesame2Status.Locked
                if received_mechstatus.isInLockRange()
                else CHSesame2Status.Unlocked
            )
        elif publish_payload.getCmdItCode() == BleItemCode.mechSetting:
            received_mechsetting = CHSesameBotMechSettings(
                rawdata=publish_payload.getPayload()
            )

            logger.debug(f"onGattSesamePublish: recieved {str(received_mechsetting)}")
            self.setMechSetting(received_mechsetting)

    async def click(self, history_tag: str = "pysesameos2") -> None:
        """Click.

        Args:
            history_tag (str): The key tag to sent when locking and unlocking. Defaults to `pysesameos2`.
        """
        if self.getDeviceStatus().value == CHDeviceLoginStatus.UnLogin:
            raise RuntimeError("No device connenction.")

        logger.info(f"Click: UUID={self.getDeviceUUID()}, history_tag={history_tag}")
        await self.sendCommand(
            CHSesame2BlePayload(
                BleOpCode.async_,
                BleItemCode.click,
                HistoryTagHelper.create_htag(history_tag),
            ),
            BleCommunicationType.ciphertext,
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

    async def toggle(self, history_tag: str = "pysesameos2") -> None:
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
            await self.unlock(history_tag=history_tag)
        elif status.isInUnlockRange():
            await self.lock(history_tag=history_tag)

    def __str__(self) -> str:
        """Return a string representation of an object.

        Returns:
            str: The string representation of the object.
        """
        return f"CHSesameBot(deviceUUID={self.getDeviceUUID()}, deviceModel={self.productModel}, mechStatus={self.getMechStatus()})"
