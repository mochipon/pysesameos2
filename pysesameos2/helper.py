from __future__ import annotations

import importlib
from enum import Enum
from typing import Generator, Union


class CHProductModel(Enum):
    WM2 = {
        "deviceModel": "wm_2",
        "isLocker": False,
        "productType": 1,
        "deviceFactory": None,
    }
    SS2 = {
        "deviceModel": "sesame_2",
        "isLocker": True,
        "productType": 0,
        "deviceFactory": "CHSesame2",
    }

    def getByModel(model: str) -> Union[CHProductModel, None]:
        if not isinstance(model, str):
            raise ValueError("Invalid Model")
        return next(
            (e for e in list(CHProductModel) if e.value["deviceModel"] == model), None
        )

    def getByValue(val: int) -> Union[CHProductModel, None]:
        if not isinstance(val, int):
            raise ValueError("Invalid Value")
        return next(
            (e for e in list(CHProductModel) if e.value["productType"] == val), None
        )

    def deviceModel(self) -> str:
        return self.value["deviceModel"]

    def isLocker(self) -> bool:
        return self.value["isLocker"]

    def productType(self) -> int:
        return self.value["productType"]

    def deviceFactory(self) -> Union[type, None]:
        if self.value["deviceFactory"] is not None:
            return getattr(
                importlib.import_module(
                    f"pysesameos2.{self.value['deviceFactory'].lower()}"
                ),
                self.value["deviceFactory"],
            )
        else:
            return None


class CHSesame2MechStatus:
    def __init__(self, rawdata: Union[bytes, str]) -> None:
        """Represent a mechanical status of a device.

        Args:
            rawdata (Union[bytes, str]): The rawdata from the device.
        """
        if isinstance(rawdata, str):
            data = bytes.fromhex(rawdata)
        elif isinstance(rawdata, bytes):
            data = rawdata
        else:
            raise TypeError("Invalid CHSesame2MechStatus")

        self._data = data
        self._batteryVoltage = int.from_bytes(data[0:2], "little") * 7.2 / 1023
        self._target = int.from_bytes(data[2:4], "little", signed=True)
        self._position = int.from_bytes(data[4:6], "little", signed=True)
        self._retcode = data[6]
        self._isInLockRange = data[7] & 2 > 0
        self._isInUnlockRange = data[7] & 4 > 0
        self._isBatteryCritical = data[7] & 32 > 0

    def __str__(self) -> str:
        return f"CHSesame2MechStatus(Battery={self.getBatteryPrecentage()}% ({self.getBatteryVoltage():.2f}V), isInLockRange={self.isInLockRange()}, isInUnlockRange={self.isInUnlockRange()}, Position={self.getPosition()})"

    def getBatteryPrecentage(self) -> int:
        """Return battery status information as a percentage.

        Returns:
            int: Battery power left as a percentage.
        """
        list_vol = [6.0, 5.8, 5.7, 5.6, 5.4, 5.2, 5.1, 5.0, 4.8, 4.6]
        list_pct = [100.0, 50.0, 40.0, 32.0, 21.0, 13.0, 10.0, 7.0, 3.0, 0.0]
        cur_vol = self._batteryVoltage

        if cur_vol >= list_vol[0]:
            return 100
        elif cur_vol <= list_vol[-1]:
            return 0
        else:
            ret = 0
            i = 0
            while i < len(list_vol) - 1:
                if cur_vol > list_vol[i] or cur_vol <= list_vol[i + 1]:
                    i = i + 1
                    continue
                else:
                    f = (cur_vol - list_vol[i + 1]) / (list_vol[i] - list_vol[i + 1])
                    f3 = list_pct[i]
                    f4 = list_pct[i + 1]
                    ret = int(f4 + (f * (f3 - f4)))
                    break

            return ret

    def getBatteryVoltage(self) -> float:
        """Return battery status information as a voltage.

        Returns:
            float: Battery power left as a voltage.
        """
        return self._batteryVoltage

    def getPosition(self) -> int:
        """Return current potision.

        Returns:
            int: The current position (-32767~0~32767)
        """
        return self._position

    def getRetCode(self) -> int:
        """Return a return code.

        Returns:
            int: The result for a locking/unlocking request.
        """
        return self._retcode

    def getTarget(self) -> int:
        """Return target potision.

        Returns:
            int: The target position (-32767~0~32767)
        """
        return self._target

    def isInLockRange(self) -> bool:
        """Return whether a device is currently locked.

        Returns:
            bool: `True` if it is locked, `False` if not.
        """
        return self._isInLockRange

    def isInUnlockRange(self) -> bool:
        """Return whether a device is currently unlocked.

        Returns:
            bool: `True` if it is unlocked, `False` if not.
        """
        return self._isInUnlockRange


class CHSesame2MechSettings:
    def __init__(self, rawdata: Union[bytes, str]) -> None:
        """Represent mechanical setting of a device.

        Args:
            rawdata (Union[bytes, str]): The rawdata from the device.
        """
        if isinstance(rawdata, str):
            data = bytes.fromhex(rawdata)
        elif isinstance(rawdata, bytes):
            data = rawdata
        else:
            raise TypeError("Invalid CHSesame2MechSettings")

        self._data = data
        self._lockPosition = int.from_bytes(data[0:2], "little", signed=True)
        self._unlockPosition = int.from_bytes(data[2:4], "little", signed=True)

    @property
    def isConfigured(self) -> bool:
        """Return whether the settings related to locking are complete.

        Returns:
            bool: `True` if configured, `False` if not.
        """
        return self.getLockPosition() != self.getUnlockPosition()

    def getLockPosition(self) -> int:
        """Return an angle of a key to be locked.

        Returns:
            int: The key position (-32767~0~32767)
        """
        return self._lockPosition

    def getUnlockPosition(self) -> int:
        """Return an angle of a key to be unlocked.

        Returns:
            int: The key position (-32767~0~32767)
        """
        return self._unlockPosition

    def __str__(self) -> str:
        return f"CHSesame2MechSettings(LockPosition={self.getLockPosition()}, UnlockPosition={self.getUnlockPosition()}, isConfigured={self.isConfigured})"


class HistoryTagHelper:
    def split_utf8(s: bytes, n: int) -> Generator[bytes, None, None]:
        """
        Split UTF-8 s into chunks of maximum length n.

        https://stackoverflow.com/questions/6043463/
        """
        while len(s) > n:
            k = n
            while (s[k] & 0xC0) == 0x80:
                k -= 1
            yield s[:k]
            s = s[k:]
        yield s

    def create_htag(history_tag: str) -> bytes:
        """Create a bytes representation of a history tag.

        `(header[1 bytes]: length of the body) + (body: utf-8 encoded string) + (padding)`

        Note that the length of a tag is always 22 bytes, thereby the body part should be
        21 bytes or less.

        Args:
            history_tag (str): The string part of the history tag.

        Returns:
            bytes: The bytes representation of the history tag.
        """
        htag_body = next(HistoryTagHelper.split_utf8(history_tag.encode("utf-8"), 21))
        htag_prefix = bytes([len(htag_body)])
        htag_suffix = bytes([0]) * (22 - len(htag_prefix + htag_body))
        htag = htag_prefix + htag_body + htag_suffix
        return htag
