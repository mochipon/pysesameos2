_English follows Japanese._

# MQTT - SESAME Bridge

このスクリプトは MQTT サーバと SESAME3 スマートロックの間をブリッジ接続します。[Home Assistant](https://www.home-assistant.io/) の [MQTT Lock](https://www.home-assistant.io/integrations/lock.mqtt/) を使うことで、鍵の状態をリアルタイムに把握したり、操作したりすることができます。

## ⚠️ 注意とおねがい

このスクリプトは、`pysesameos2` が正しく動く ~~っぽい~~ ことを確かめる目的で作られており、本番環境で広くあまねく使われることを意図していません。

例えば、`pysesameos2` と SESAME OS2 が動作するデバイスの間でやりとりされる通信は相互認証を含めた暗号化処理が行われています。一方で、このスクリプトは MQTT サーバに対して平文で通信します。結果的に、SESAME OS2 が動作するデバイスのセキュリティは低下してしまいます。

このサンプルスクリプトを含めて `pysesameos2` に関する問題の報告や Pull Request は常に大歓迎しています。これらを公開する目的は、必要とする方々に使って頂くことはもちろんですが、みなさんの力を借りることで (わたしひとりでは困難な) 問題の発見や品質の向上を夢見ているからです。

## 検証環境

* macOS 10.15.7, Python 3.9.5
* Raspberry Pi Zero W (Raspbian GNU/Linux 10, Raspberry Pi reference 2021-05-07), Python 3.7.3

## 環境構築の例 (Raspberry Pi Zero W)

1. 最新の Raspberry Pi OS をインストールする
2. `git`, `pip` `virtualenv` をインストールする
```console
# apt install git python3-pip python3-virtualenv
```
3. スクリプトをダウンロードする
```console
$ git clone https://github.com/mochipon/pysesameos2.git
```
4. 必要なライブラリをインストールする
```console
$ cd pysesameos2/example/mqtt2sesame
$ virtualenv venv
$ . venv/bin/activate
$ pip install -r requirements.txt
```
5. Bluetooth を使うために必要な権限をユーザに付与する
```console
# usermod -a -G bluetooth $USER
# reboot
```

## スクリプトの利用方法

1. `discover.py` を実行して、Bluetooth における UUID と SESAME デバイスの UUID (アプリに表示される UUID) の対応を取得します。

```console
$ . venv/bin/activate
$ python discover.py
==========
BLE Device Identifier: 00:11:22:AA:BB:CC
SESAME Device Identifier: 9F8867D5-4FEF-48CA-BF74-1620FF9006F1
==========
```

2. 取得した情報を元にして `config.yml` を作成します。
Bluetooth における UUID とそれに対応するデバイスの `secret_key`, `public_key` を紐付けます。

3. `mqtt2sesame.py` を実行します

## Home Assistant の設定例

```yaml
lock:
  - platform: mqtt
    name: 上の鍵
    unique_id: 9F8867D5-4FEF-48CA-BF74-1620FF9006F1
    state_topic: pysesameos2/9F8867D5-4FEF-48CA-BF74-1620FF9006F1/status
    command_topic: pysesameos2/9F8867D5-4FEF-48CA-BF74-1620FF9006F1/cmd
    qos: 1
    availability_topic: pysesameos2/LWT
```

- - -

# MQTT - SESAME Bridge

This program aims to retrieve and control the status of SESAME devices via MQTT. Compatible with [Home Assistant](https://www.home-assistant.io/)'s [MQTT Lock](https://www.home-assistant.io/integrations/lock.mqtt/) platform.

## ⚠️ Important

This script is intended to demonstrate the use of `pysesameos2` and is **not recommended for use in production**.

For instance, security considerations such as mutual authentication are provided between `pysesameos2` and SESAME devices, but the communication to the MQTT server is in plaintext. 😱

PRs are always welcome! We'll all be happy to see that it's not just a sample, but of production-ready. 🙌

## Tested Environments

* macOS 10.15.7, Python 3.9.5
* Raspberry Pi Zero W (Raspbian GNU/Linux 10, Raspberry Pi reference 2021-05-07), Python 3.7.3

## Usage

1. In order to connect to a device via Bluetooth, we need to find out the Bluetooth identifier (address) of the device. Run `discover.py` and it shows the mapping between the Bluetooth address and the SESAME UUID.
2. Edit `config.yml` accordingly.
3. Run `mqtt2sesame.py`.
