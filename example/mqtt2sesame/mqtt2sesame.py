from __future__ import annotations

import argparse
import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Dict, NamedTuple, Optional

import paho.mqtt.client as mqtt
import yaml

from pysesameos2.ble import CHBleManager
from pysesameos2.const import CHDeviceLoginStatus, CHSesame2Status

if TYPE_CHECKING:
    from paho.mqtt.client import MQTTMessage

    from pysesameos2.chsesame2 import CHSesame2
    from pysesameos2.device import CHDevices


logging.basicConfig()
logging.getLogger("bleak").setLevel(level=logging.INFO)
logger = logging.getLogger(__name__)

mqtt_client = mqtt.Client()
with open("config.yml", "r") as yml:
    config = yaml.safe_load(yml)
cmd_queue = None
connected_devices = None


class Sesame2Device(NamedTuple):
    device: CHSesame2
    ble_uuid: str


async def connect_sesame(ble_device_identifier: str, **kwargs) -> CHSesame2:
    blem = CHBleManager()

    device = await blem.scan_by_address(
        ble_device_identifier=ble_device_identifier, scan_duration=30
    )
    if device is None:
        raise ConnectionRefusedError("Failed in scanning the device.")
    if not isinstance(device, CHSesame2):
        raise ValueError("Not a CHSesame2 device.")

    device.setDeviceStatusCallback(onSesameStateChanged)
    device.getKey().setSecretKey(kwargs.get("secret_key"))
    device.getKey().setSesame2PublicKey(kwargs.get("public_key"))

    await device.connect()
    await device.wait_for_login()

    return device


async def runner_connect_sesame(
    target_ble_uuid: Optional[str] = None,
) -> Dict[str, Sesame2Device]:
    if target_ble_uuid is None:
        target_devices = config["sesame"]
    else:
        if target_ble_uuid not in config["sesame"]:
            raise ValueError("Unknown BLE UUID.")
        else:
            target_devices = {target_ble_uuid: config["sesame"][target_ble_uuid]}

    pending_tasks = set()
    for ble_uuid, sesame_config in target_devices.items():
        logger.debug("Connect to the Sesame device: BLE UUID = {}".format(ble_uuid))
        pending_tasks.add(
            asyncio.create_task(connect_sesame(ble_uuid, **sesame_config))
        )

    connected_devices = {}
    while pending_tasks:
        done_tasks, pending_tasks = await asyncio.wait(
            pending_tasks, return_when=asyncio.FIRST_EXCEPTION
        )
        for task in done_tasks:
            if task.exception():
                ble_uuid = inspect.getargvalues(task.get_stack()[0]).locals[
                    "ble_device_identifier"
                ]
                sesame_config = config["sesame"][ble_uuid]
                pending_tasks.add(
                    asyncio.create_task(connect_sesame(ble_uuid, **sesame_config))
                )
                logger.warning("Connection retry: BLE UUID = {}".format(ble_uuid))
            else:
                device = task.result()
                ble_uuid = device.getAdvertisement().getAddress()
                connected_devices[device.deviceId] = Sesame2Device(device, ble_uuid)
                logger.info(
                    "Connected: BLE UUID = {}, SESAME UUID = {}".format(
                        ble_uuid, device.deviceId
                    )
                )

    return connected_devices


def onSesameStateChanged(device: CHDevices) -> None:
    global mqtt_client, config
    logger.info(
        "SESAME status changed: SESAME UUID={}, status={}".format(
            device.deviceId, device.getDeviceStatus()
        )
    )

    topic = "{}/{}/status".format(config["mqtt"]["topic_prefix"], device.deviceId)
    payload = None
    if device.getDeviceStatus() == CHSesame2Status.Locked:
        payload = "LOCKED"
    elif device.getDeviceStatus() == CHSesame2Status.Unlocked:
        payload = "UNLOCKED"

    if payload:
        logger.info("Publish a message: topic={}, payload={}".format(topic, payload))
        mqtt_client.publish(topic, payload=payload, qos=1, retain=True)


def onMQTTMessage(client, userdata, msg: MQTTMessage) -> None:
    global cmd_queue

    logger.info(
        "Received a cmd message: topic={}, payload={}".format(msg.topic, msg.payload)
    )
    uuid = msg.topic.split("/")[1]
    cmd = msg.payload.decode("utf-8")

    if cmd_queue and (cmd == "LOCK" or cmd == "UNLOCK"):
        cmd_queue.put_nowait((uuid, cmd))


async def runner():
    global mqtt_client, config, cmd_queue, connected_devices

    cmd_queue = asyncio.Queue()

    lwt_topic = "{}/LWT".format(config["mqtt"]["topic_prefix"])
    mqtt_client.will_set(lwt_topic, payload="offline", qos=1, retain=True)
    mqtt_client.on_message = onMQTTMessage
    mqtt_client.username_pw_set(config["mqtt"]["username"], config["mqtt"]["password"])

    logger.info("Connect to the MQTT server: {}".format(config["mqtt"]["host"]))
    mqtt_client.connect(config["mqtt"]["host"], config["mqtt"]["port"])
    cmd_topic = "{}/+/cmd".format(config["mqtt"]["topic_prefix"])
    logger.debug("Subscribe to the MQTT topic: {}".format(cmd_topic))
    mqtt_client.subscribe(cmd_topic, qos=0)

    connected_devices = await runner_connect_sesame()

    logger.debug("Publish a message: topic={}, payload=online".format(lwt_topic))
    mqtt_client.publish(lwt_topic, payload="online", qos=1, retain=True)

    while True:
        for sesame_uuid, sesame_device in connected_devices.items():
            if sesame_device.device.getDeviceStatus().value == CHDeviceLoginStatus.UnLogin:  # type: ignore
                ble_uuid = sesame_device.ble_uuid
                logger.error(
                    "Found disconnected device, retry: BLE UUID = {}, SESAME UUID = {}".format(
                        ble_uuid, sesame_uuid
                    )
                )
                new_connection = await runner_connect_sesame(ble_uuid)
                connected_devices[sesame_uuid] = new_connection[sesame_uuid]

        try:
            sesame_uuid, command = await asyncio.wait_for(cmd_queue.get(), timeout=1.0)
            sesame_device = connected_devices.get(sesame_uuid)
            if sesame_device is not None:
                if command == "LOCK":
                    logger.info("Execute locking: SESAME UUID = {}".format(sesame_uuid))
                    await sesame_device.device.lock()
                elif command == "UNLOCK":
                    logger.info(
                        "Execute unlocking: SESAME UUID = {}".format(sesame_uuid)
                    )
                    await sesame_device.device.unlock()
        except asyncio.TimeoutError:
            pass

        mqtt_client.loop()


async def cleanup():
    global mqtt_client

    logger.info("Cleanup...")

    lwt_topic = "{}/LWT".format(config["mqtt"]["topic_prefix"])
    logger.debug("Publish a message: topic={}, payload=offline".format(lwt_topic))
    mqtt_client.publish(lwt_topic, payload="offline", qos=1, retain=True)
    mqtt_client.disconnect()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    args = parser.parse_args()
    logger.setLevel(level=args.loglevel)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()
