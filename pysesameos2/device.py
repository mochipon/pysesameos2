import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from bleak.backends.characteristic import BleakGATTCharacteristic

from pysesameos2.const import CHDeviceLoginStatus, CHSesame2Intention, CHSesame2Status
from pysesameos2.crypto import BleCipher

if TYPE_CHECKING:
    from pysesameos2.ble import BLEAdvertisement
    from pysesameos2.helper import CHProductModel

logger = logging.getLogger(__name__)


class CHDeviceKey:
    def __init__(self) -> None:
        self._secretKey: Optional[bytes] = None
        self._sesame2PublicKey: Optional[bytes] = None

        # According to the spec, this is fixed (;_;)...
        self._keyindex = bytes.fromhex("0000")

    def getSecretKey(self) -> Optional[bytes]:
        """Return a secret key of a specific device.

        Returns:
            str: The secret key for controlling the device.
        """
        return self._secretKey

    def getSesame2PublicKey(self) -> Optional[bytes]:
        """Return a public key of a specific device.

        Returns:
            str: The public key of the device.
        """
        return self._sesame2PublicKey

    def getKeyIndex(self) -> bytes:
        """Return a index of a key.

        Returns:
            str: The index of the key
        """
        return self._keyindex

    def setSecretKey(self, key: Union[bytes, str]) -> None:
        """Set a secret key for a specific device.

        Args:
            key (str): The secret key for controlling the device.

        Raises:
            ValueError: If `key` is invalid.
        """
        if not isinstance(key, bytes) and not isinstance(key, str):
            raise TypeError("Invalid SecretKey - should be str or bytes.")
        if not isinstance(key, bytes):
            key = bytes.fromhex(key)
        if len(key) != 16:
            raise ValueError("Invalid SecretKey - length should be 16.")
        self._secretKey = key

    def setSesame2PublicKey(self, key: Union[bytes, str]) -> None:
        """Set a public key of a specific device.

        Args:
            key (str): The public key of the device.

        Raises:
            ValueError: If `key` is invalid.
        """
        if not isinstance(key, bytes) and not isinstance(key, str):
            raise TypeError("Invalid Sesame2PublicKey - should be str or bytes.")
        if not isinstance(key, bytes):
            key = bytes.fromhex(key)
        if len(key) != 64:
            raise ValueError("Invalid Sesame2PublicKey - length should be 64.")
        self._sesame2PublicKey = key


class CHDevices:
    def __init__(self) -> None:
        """Generic Implementation for Candyhouse products."""
        self._deviceId: Optional[uuid.UUID] = None
        self._productModel: Optional[CHProductModel] = None
        self._registered: bool = False
        self._rssi: int = -100
        self._deviceStatus: CHSesame2Status = CHSesame2Status.NoBleSignal  # type: ignore
        self._deviceStatus_callback: Optional[Callable[[CHDevices], None]] = None
        self._advertisement: Optional[BLEAdvertisement] = None
        self._key: CHDeviceKey = CHDeviceKey()
        self._login_event = asyncio.Event()

    @property
    def deviceId(self) -> Optional[str]:
        """Return a device id of a specific device.

        Returns:
            str: The UUID of the device.
        """
        if self._deviceId is not None:
            return str(self._deviceId).upper()
        else:
            return None

    @property
    def productModel(self) -> Optional["CHProductModel"]:
        """Return a model information of a specific device.

        Returns:
            CHProductModel: The product model of the device.
        """
        return self._productModel

    def getRssi(self) -> int:
        """Return a received signal strength indicator in dBm.

        Returns:
            rssi (int): The RSSI.
        """
        return self._rssi

    def getDeviceStatus(self) -> CHSesame2Status:
        """Return a current status of a device.

        Returns:
            status (CHSesame2Status): The status of the device.
        """
        return self._deviceStatus  # type: ignore

    def getRegistered(self) -> bool:
        """Return a status of whether a device is already registed with the server.

        Returns:
            bool: `True` if the device is registed, `False` if not.
        """
        return self._registered

    def getAdvertisement(self) -> Optional["BLEAdvertisement"]:
        """Return a cached BLE advertisement.

        Returns:
            BLEAdvertisement: The advertisement from the device.
        """
        return self._advertisement

    def getKey(self) -> CHDeviceKey:
        """Return a key object for a device.

        Returns:
            CHDeviceKey: The key object for the device.
        """
        return self._key

    def setDeviceId(self, id: Union[uuid.UUID, str]) -> None:
        """Set a device id of a specific device.

        Args:
            id (Union[uuid.UUID, str]): The UUID of the device.

        Raises:
            ValueError: If `id` is invalid.
        """
        if isinstance(id, str):
            id = uuid.UUID(id)
        elif not isinstance(id, uuid.UUID):
            raise TypeError("Invalid UUID")
        self._deviceId = id

    def setProductModel(self, model: "CHProductModel") -> None:
        """Set a model information of a specific device.

        Args:
            model (CHProductModel): The product model of the device.

        Raises:
            ValueError: If `model` is invalid.
        """
        if type(model).__name__ != "CHProductModel":
            raise TypeError("Invalid CHProductModel")
        self._productModel = model

    def setRssi(self, rssi: int) -> None:
        """Set a received signal strength indicator in dBm.

        Args:
            rssi (int): The RSSI.
        """
        if not isinstance(rssi, int):
            raise TypeError("Invalid RSSI - should be int.")
        self._rssi = rssi

    def setDeviceStatus(self, status: Any) -> None:
        """Set a current status of a device.

        Args:
            status (CHSesame2Status): The status of the device.
        """
        if not isinstance(status, CHSesame2Status):
            raise TypeError("Invalid Device Status")

        if status != self.getDeviceStatus():
            self._deviceStatus = status
            if self._deviceStatus_callback:
                self._deviceStatus_callback(self)
            if self._deviceStatus.value == CHDeviceLoginStatus.UnLogin:
                self._login_event.clear()
            elif self._deviceStatus.value == CHDeviceLoginStatus.Login:
                self._login_event.set()

    def setRegistered(self, isRegistered: bool) -> None:
        """Set a status of whether a device is already registed with the server.

        Args:
            isRegistered (bool): `True` if the device is registed, `False` if not.
        """
        if not isinstance(isRegistered, bool):
            raise TypeError("Invalid Registered Status - should be bool.")

        self._registered = isRegistered

    def setAdvertisement(self, adv: Optional["BLEAdvertisement"] = None) -> None:
        """Get device information based on BLE advertisements and set properties accordingly.

        Args:
            adv (BLEAdvertisement): The advertisement from the device. Defaults to `None`.

        Raises:
            ValueError: If the device is not registred.
        """
        if adv is not None and type(adv).__name__ != "BLEAdvertisement":
            raise TypeError("Invalid BLEAdvertisement")
        else:
            self._advertisement = adv

        if adv is None:
            logger.debug("setAdvertisement: Reset the status")
            self.setDeviceStatus(CHSesame2Status.NoBleSignal)
            self.setRssi(-100)
            return

        if adv.isRegistered() is False:
            raise RuntimeError(
                "This device is not supported: initial configuration needed from the official mobile app."
            )

        logger.debug(f"setAdvertisement: Product Model = {adv.getProductModel()}")
        self.setProductModel(adv.getProductModel())

        logger.debug(f"setAdvertisement: RSSI = {adv.getRssi()}")
        self.setRssi(adv.getRssi())

        logger.debug(f"setAdvertisement: Device ID (UUID) = {adv.getDeviceID()}")
        self.setDeviceId(adv.getDeviceID())

        logger.debug(f"setAdvertisement: isRegistered = {adv.isRegistered()}")
        self.setRegistered(adv.isRegistered())

        if self.getDeviceStatus() == CHSesame2Status.NoBleSignal:
            self.setDeviceStatus(CHSesame2Status.ReceivedBle)

    def setDeviceStatusCallback(
        self, callback: Optional[Callable[["CHDevices"], None]]
    ) -> None:
        """Set a device status callback.

        Args:
            callback (Optional[Callable[[CHDevices], None]]): The callback to be called on device status changing.
        """
        if callback is not None and not callable(callback):
            raise TypeError("Invalid DeviceStatusCallback")

        self._deviceStatus_callback = callback

    def setKey(self, key: CHDeviceKey) -> None:
        """Set a key object for a device.

        Args:
            key (CHDeviceKey): The key object for the device.
        """
        if not isinstance(key, CHDeviceKey):
            raise TypeError("Invalid key")

        self._key = key

    async def wait_for_login(self):
        return await self._login_event.wait()


class CHSesameLock(CHDevices):
    def __init__(self) -> None:
        """Generic Implementation for Candyhouse smart locks."""
        super().__init__()
        self._intention: CHSesame2Intention = CHSesame2Intention.idle
        self._characteristicTX: Optional[BleakGATTCharacteristic] = None
        self._sesameToken: Optional[bytes] = None
        self._cipher: Optional[BleCipher] = None

    def getDeviceUUID(self) -> Optional[str]:
        """Return a device UUID of a specific device.

        Returns:
            str: The UUID of the device.
        """
        return self.deviceId

    def getIntention(self) -> CHSesame2Intention:
        """Get a mechanical intention of a device.

        Returns:
            CHSesame2Intention: The indention of the device.
        """
        return self._intention

    def getCharacteristicTX(self) -> Optional[BleakGATTCharacteristic]:
        """Get a cached BleakGATTCharacteristic object.

        Returns:
            BleakGATTCharacteristic: The GATT characteristic to send data.
        """
        return self._characteristicTX

    def getCipher(self) -> Optional[BleCipher]:
        """Get an object to process encryption/decryption of data.

        Returns:
            BleCipher: The object for processing encryption and decryption.
        """
        return self._cipher

    def getSesameToken(self) -> Optional[bytes]:
        """Return a cached token which is received from a device during its login process.

        Returns:
            bytes: The token bytes.
        """
        return self._sesameToken

    def setDeviceUUID(self, id: Union[uuid.UUID, str]) -> None:
        """Set a device UUID of a specific device.

        Args:
            id (Union[uuid.UUID, str]): The UUID of the device.
        """
        return self.setDeviceId(id)

    def setIntention(self, intent: CHSesame2Intention) -> None:
        """Set a mechanincal intention of a device.

        Args:
            intent (CHSesame2Intention): The indention of the device.
        """
        if not isinstance(intent, CHSesame2Intention):
            raise TypeError("Invalid Intention.")

        self._intention = intent

    def setCharacteristicTX(self, ble_char: BleakGATTCharacteristic) -> None:
        """Cache a BleakGATTCharacteristic.

        Args:
            ble_char (BleakGATTCharacteristic): The GATT characteristic to send data.
        """
        if not isinstance(ble_char, BleakGATTCharacteristic):
            raise TypeError("Invalid Characteristic")
        self._characteristicTX = ble_char

    def setCipher(self, cipher: BleCipher) -> None:
        """Set an object to process encryption/decryption of data.

        Args:
            cipher (BleCipher): The object for processing encryption and decryption.
        """
        if not isinstance(cipher, BleCipher):
            raise TypeError("Invalid Cipher")
        self._cipher = cipher

    def setSesameToken(self, token: bytes) -> None:
        """Cache a token which is received from a device during its login process.

        Args:
            token (bytes): The token bytes.
        """
        if not isinstance(token, bytes):
            raise TypeError("Invalid SesameToken")
        self._sesameToken = token

    def __str__(self) -> str:
        """Returns a string representation of an object.

        Returns:
            str: The string representation of the object.
        """
        return f"CHSesameLock(deviceUUID={self.getDeviceUUID()}, deviceModel={self.productModel})"
