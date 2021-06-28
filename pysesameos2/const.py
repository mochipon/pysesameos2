from enum import Enum, auto

import aenum

SERVICE_UUID = "0000fd81-0000-1000-8000-00805f9b34fb"
TX_UUID = "16860002-a5ae-9856-b6d3-dbb4c676993e"
RX_UUID = "16860003-a5ae-9856-b6d3-dbb4c676993e"


class CHDeviceLoginStatus(Enum):
    Login = auto()
    UnLogin = auto()


class CHSesame2Status(aenum.Enum, settings=aenum.NoAlias):  # type: ignore
    NoBleSignal = CHDeviceLoginStatus.UnLogin
    ReceivedBle = CHDeviceLoginStatus.UnLogin
    BleConnecting = CHDeviceLoginStatus.UnLogin
    WaitingGatt = CHDeviceLoginStatus.UnLogin
    BleLogining = CHDeviceLoginStatus.UnLogin
    Registering = CHDeviceLoginStatus.UnLogin
    ReadyToRegister = CHDeviceLoginStatus.UnLogin
    WaitingForAuth = CHDeviceLoginStatus.UnLogin
    NoSettings = CHDeviceLoginStatus.Login
    Reset = CHDeviceLoginStatus.UnLogin
    DfuMode = CHDeviceLoginStatus.UnLogin
    Busy = CHDeviceLoginStatus.UnLogin
    Locked = CHDeviceLoginStatus.Login
    Moved = CHDeviceLoginStatus.Login
    Unlocked = CHDeviceLoginStatus.Login
    WaitApConnect = CHDeviceLoginStatus.Login
    IotConnected = CHDeviceLoginStatus.Login
    IotDisconnected = CHDeviceLoginStatus.Login


class BleItemCode(Enum):
    none = 0
    registration = 1
    login = 2
    user = 3
    history = 4
    versionTag = 5
    disconnectRebootNow = 6
    enableDFU = 7
    time = 8
    bleConnectionParam = 9
    bleAdvParam = 10
    autolock = 11
    serverAdvKick = 12
    ssmtoken = 13
    initial = 14
    IRER = 15
    timePhone = 16
    mechSetting = 80
    mechStatus = 81
    lock = 82
    unlock = 83
    moveTo = 84
    driveDirection = 85
    stop = 86
    detectDir = 87
    toggle = 88
    click = 89


class BleOpCode(Enum):
    create = 1
    read = 2
    update = 3
    delete = 4
    sync = 5
    async_ = 6
    response = 7
    publish = 8
    undefine = 16


class BleCommunicationType(Enum):
    plaintext = 1
    ciphertext = 2


class BlePacketType(Enum):
    APPEND_ONLY = 0
    isStart = 1
    NotStart = 0


class BleCmdResultCode(Enum):
    success = 0
    invalidFormat = 1
    notSupported = 2
    StorageFail = 3
    invalidSig = 4
    notFound = 5
    UNKNOWN = 6
    BUSY = 7
    INVALID_PARAM = 8


class CHSesame2Intention(Enum):
    movingToUnknownTarget = auto()
    locking = auto()
    unlocking = auto()
    holding = auto()
    idle = auto()
