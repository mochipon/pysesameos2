# pysesameos2

_Unofficial Python Library to communicate with SESAME products via Bluetooth._

[![PyPI](https://img.shields.io/pypi/v/pysesameos2)](https://pypi.python.org/pypi/pysesameos2)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pysesameos2)
![GitHub Workflow Status (branch)](https://img.shields.io/github/workflow/status/mochipon/pysesameos2/dev%20workflow/main)
[![Documentation Status](https://readthedocs.org/projects/pysesameos2/badge/?version=latest)](https://pysesameos2.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/mochipon/pysesameos2/branch/main/graph/badge.svg?token=EOkDeLXeG2)](https://codecov.io/gh/mochipon/pysesameos2)
![PyPI - License](https://img.shields.io/pypi/l/pysesameos2)

## Introduction

This project aims to control smart devices running **Sesame OS2** via **Bluetooth**. If you want to control them via the cloud service, please check [pysesame3](https://github.com/mochipon/pysesame3).

To be honest, this is my first time to use [`Bleak`](https://github.com/hbldh/bleak) which provides an asynchronous, cross-platform Bluetooth API. PRs are heavily welcome.

* Free software: MIT license
* Documentation: [https://pysesameos2.readthedocs.io](https://pysesameos2.readthedocs.io)

## Tested Environments

* macOS 10.15.7, Python 3.9.5
* Raspberry Pi Zero W (Raspbian GNU/Linux 10, Raspberry Pi reference 2021-05-07), Python 3.7.3

## Supported devices

- [SESAME 3](https://jp.candyhouse.co/products/sesame3)
- [SESAME 4](https://jp.candyhouse.co/products/sesame4)
- [SESAME bot](https://jp.candyhouse.co/products/sesame3-bot)

## Features

* Scan all SESAME locks using BLE advertisements.
* Receive state changes (locked, handle position, etc.) that are actively reported from the device.
* Needless to say, locking and unlocking!

## Consideration

- The results of `pysesameos2` are merely from reverse engineering of [the official SDK](https://doc.candyhouse.co/). We have implemented just a small part of it, so you might run into some issues. Please do let me know if you find any problems!
- `pysesameos2` only supports devices that have already been initially configured using the official app. That is, `pysesameos2` cannot configure the locking position of your device.
- `pysesameos2` does not have, and will not have, any functionality related to the operation history of locks.  According to [the document](https://doc.candyhouse.co/ja/flow_charts#sesame-%E5%B1%A5%E6%AD%B4%E6%A9%9F%E8%83%BD), your lock's operation history is not stored in the lock itself, but on the cloud service. I personally recommend you to bring a Wi-Fi module to get the operation history uploaded and retrive it by [the API](https://doc.candyhouse.co/ja/SesameAPI#sesame%E3%81%AE%E5%B1%A5%E6%AD%B4%E3%82%92%E5%8F%96%E5%BE%97).

## Usage

Please take a look at the [`example`](https://github.com/mochipon/pysesameos2/tree/main/example) directory.

## Related Projects

### Libraries
| Name | Lang | Communication Method |
----|----|----
| [pysesame](https://github.com/trisk/pysesame) | Python | [Sesame API v1/v2](https://docs.candyhouse.co/v1.html)
| [pysesame2](https://github.com/yagami-cerberus/pysesame2) | Python | [Sesame API v3](https://docs.candyhouse.co/)
| [pysesame3](https://github.com/mochipon/pysesame3) | Python | [Web API](https://doc.candyhouse.co/ja/SesameAPI), [CognitoAuth (The official android SDK reverse-engineered)](https://doc.candyhouse.co/ja/android)
| [pysesameos2](https://github.com/mochipon/pysesameos2) | Python | [Bluetooth](https://doc.candyhouse.co/ja/android)

### Integrations
| Name | Description | Communication Method |
----|----|----
| [doorman](https://github.com/jp7eph/doorman) | Control SESAME3 from Homebridge by MQTT | [Web API](https://doc.candyhouse.co/ja/SesameAPI)
| [Doorlock](https://github.com/kishikawakatsumi/Doorlock) | iOS widget for Sesame 3 smart lock | [Web API](https://doc.candyhouse.co/ja/SesameAPI)
| [gopy-sesame3](https://github.com/orangekame3/gopy-sesame3) | NFC (Felica) integration | [Web API](https://doc.candyhouse.co/ja/SesameAPI)
| [homebridge-open-sesame](https://github.com/yasuoza/homebridge-open-sesame) | Homebridge plugin for SESAME3 | Cognito integration
| [homebridge-sesame-os2](https://github.com/nzws/homebridge-sesame-os2) | Homebridge Plugin for SESAME OS2 (SESAME3) | [Web API](https://doc.candyhouse.co/ja/SesameAPI)
| [sesame3-webhook](https://github.com/kunikada/sesame3-webhook) | Send SESAME3 status to specified url. (HTTP Post) | CognitoAuth (based on `pysesame3`)

## Credits & Thanks

* A huge thank you to all at [CANDY HOUSE](https://jp.candyhouse.co/) and their crowdfunding contributors!
* Thanks to [@Chabiichi](https://github.com/Chabiichi)-san for [the offer](https://github.com/mochipon/pysesame3/issues/25) to get my SESAME bot!
* Many thanks to [bleak](https://github.com/hbldh/bleak) and [pyzerproc](https://github.com/emlove/pyzerproc).
