from enum import Enum

from JModel import *
import JModel


class DataModel(JObject):
    def __init__(self, **kwargs):
        self.url: str = ""
        self.youtubeId: str = ""
        self.playStatus: PlayStatus = PlayStatus.Play
        self.command: Command = Command.Null
        self.benchmarkDevice: str = ""
        self.benchmarkTimestamp: float = 0.0
        self.benchmarkPlayingPosition: float = 0.0

        super().__init__(**kwargs)


class ClientInfoDataset(JObject):
    def __init__(self, **kwargs):
        # 系统信息
        self.uuid: str = ""
        self.system: str = ""
        self.system_name: str = ""
        self.name: str = ""
        self.architecture: str = ""
        self.pythonVersion: str = ""
        # 歌曲播放进度信息
        self.benchmarkTimestamp: float = 0.0
        self.benchmarkPlayingPosition: float = 0.0
        self.playStatus: PlayStatus = PlayStatus.Unknown
        # 时间差
        self.delay: float = 0.0
        self.difference: float = 0.0
        # 本地参数
        self.last_update_time: float = 0.0
        self.enabled: bool = True
        super().__init__(**kwargs)


class PlayStatus(Enum):
    Play = "play"
    Pause = "pause"
    Load = "load"
    End = "end"
    Unknown = "unknown"


class Command(Enum):
    Play = "play"
    Load = "load"
    Pause = "pause"
    Stop = "stop"
    Redress = "redress"
    SetPosition = "setPosition"
    ReBuildUUID = "rebuild_uuid"
    InformationCollection = "information_collection"
    Null = "null"


class PlayMode(Enum):
    Random = "random" # 随机播放
    Single = "single" # 单曲循环
    List = "list" # 列表播放
    ListLoop = "list_loop" # 列表循环
