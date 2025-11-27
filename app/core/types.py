from enum import Enum, IntEnum


class CoreType(str, Enum):
    XRAY = "xray"
    SING_BOX = "sing_box"


class BackendType(IntEnum):
    XRAY = 0
    SING_BOX = 1


CORE_TYPE_TO_BACKEND = {
    CoreType.XRAY: BackendType.XRAY,
    CoreType.SING_BOX: BackendType.SING_BOX,
}
