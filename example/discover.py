import asyncio
import logging

from pysesameos2.ble import CHBleManager

# In order to understand the details of pysesameos2,
# here we dare to show the detailed logs.
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("bleak").setLevel(level=logging.INFO)
logger = logging.getLogger(__name__)


async def connect(scan_duration: int = 15):
    """
    Active scan for SESAME devices.

    You may get an error here, but it's usually due to an incomplete
    or broken scan result.
    Please run the program as close to the SESAME device as possible
    and do the appropriate error handling (like try-except).
    """
    devices = await CHBleManager().scan(scan_duration=scan_duration)

    for bleuuid, device in devices.items():
        print("=" * 10)
        print("SESAME device found: {}\n".format(device.deviceId))
        print("BLE Device Identifier: {}".format(bleuuid))
        print("RSSI: {}".format(device.getRssi()))
        print("Device Model: {}".format(device.productModel))
        print(
            "Device is registered on the SESAME cloud?: {}".format(
                device.getRegistered()
            )
        )
        print("=" * 10)


if __name__ == "__main__":
    asyncio.run(connect())
