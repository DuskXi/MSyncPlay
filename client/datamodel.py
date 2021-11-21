from enum import Enum

from JModel import *
import JModel


class DataModel(JObject):
    def __init__(self, **kwargs):
        self.url: str = ""
        self.playStatus: PlayStatus = PlayStatus.Unknown
        self.Command: Command = Command.Null
        self.benchmarkDevice: str = ""
        self.benchmarkTimestamp: float = 0.0
        self.benchmarkPlayingPosition: float = 0.0

        super().__init__(**kwargs)


class PlayStatus(Enum):
    Play = "play"
    Pause = "pause"
    Load = "load"
    Unknown = "unknown"


class Command(Enum):
    Play = "play"
    Load = "load"
    Pause = "pause"
    Stop = "stop"
    Redress = "redress"
    ReBuildUUID = "rebuild_uuid"
    InformationCollection = "information_collection"
    Null = "null"
