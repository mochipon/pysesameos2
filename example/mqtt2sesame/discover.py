import asyncio
import logging

from pysesameos2.ble import CHBleManager

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("bleak").setLevel(level=logging.INFO)
logger = logging.getLogger(__name__)


async def discover(scan_duration: int = 15):
    devices = await CHBleManager().scan(scan_duration=scan_duration)

    for bleuuid, device in devices.items():
        print("=" * 10)
        print("BLE Device Identifier: {}".format(bleuuid))
        print("SESAME Device Identifier: {}".format(device.deviceId))
        print("=" * 10)


asyncio.run(discover())
