import asyncio
import os
import platform
import re
import time
import uuid

import numpy as np
import socketio
from loguru import logger

from audio import Audio
from datamodel import *


class Core:
    def __init__(self, redress_intervals):
        self.identity = ""
        self.isRun = False
        self.time_send = 0
        self.redress_frequency_time = redress_intervals
        self.list_difference = []
        self.list_delay = []
        self.difference = 0
        self.delay = 0
        self.urls = {}
        self.sio = None
        self._init_kernel()

    def _init_kernel(self):
        self.kernelInfo: DataModel = DataModel()
        self.localInfo: ClientInfoDataset = ClientInfoDataset()
        self.audio: Audio = Audio()

    def load_music(self, url, youtube_id):
        start_time = time.time()
        self.audio.load(url, youtube_id)
        logger.info(
            f"歌曲加载完毕, 耗时: {(time.time() - start_time) * 1000} ms [video_id]: {youtube_id}")

    def onPlayEnded(self):
        self.audio.isPlaying = False
        self.sio.emit("StatusUpdate",
                      {"Identity": self.identity, "StatusType": "PlayingStatus", "PlayingStatus": False})

    temp_array = []

    def redress_music(self, position, timestamp):
        self.audio.playerLayer.stop()
        self.audio.playerLayer.reset()
        self.audio.playerLayer.set_position_with_benchmark(
            position + time.time() - (timestamp - self.difference))
        self.audio.playerLayer.play()

    def get_server_timestamp(self):
        return time.time() + self.difference

    def convert_server_timestamp_to_local(self, timestamp):
        return timestamp - self.difference

    def onCommand(self, command):
        """
        有命令传入时调用
        :param command:
        :return:
        """
        if command == Command.Load:
            self.load_music(self.kernelInfo.url, self.kernelInfo.youtubeId)
            self.updateInformation()
        if command == Command.Play:
            while True:
                if time.time() > (self.kernelInfo.benchmarkTimestamp - self.difference):
                    break
                time.sleep(0.001)
            position = self.kernelInfo.benchmarkPlayingPosition
            benchmark = self.kernelInfo.benchmarkTimestamp
            self.audio.playerLayer.set_position_with_benchmark(position + time.time() - (benchmark - self.difference))
            # TODO: 总体通过后进行一些实验性更新
            self.audio.play()
        if command == Command.Pause:
            if self.audio.isPlaying:
                self.audio.pause()
            else:
                position = self.kernelInfo.benchmarkPlayingPosition
                benchmark = self.kernelInfo.benchmarkTimestamp
                self.audio.playerLayer.set_position_with_benchmark(
                    position + time.time() - (benchmark - self.difference))
                self.audio.play()
                # TODO: 这边也是
        if command == Command.Stop:
            self.audio.playerLayer.stop()
        if command == Command.Redress:
            self.redress_music(self.kernelInfo.benchmarkPlayingPosition, self.kernelInfo.benchmarkTimestamp)
        if command == Command.InformationCollection:
            self.updateInformation()
        if command == Command.SetPosition:
            self.audio.playerLayer.set_position_with_benchmark_customize(
                self.kernelInfo.benchmarkPlayingPosition,
                self.convert_server_timestamp_to_local(self.kernelInfo.benchmarkTimestamp))
            logger.info(f"设置播放位置为: {self.kernelInfo.benchmarkPlayingPosition}")

        # 命令复位
        self.kernelInfo.command = Command.Null

    def onPlayStatusChanged(self, status):
        """
        播放位发生改变时调用

        :param status:
        :return:
        """
        if self.kernelInfo.command not in [Command.Play, Command.Pause, Command.Stop]:
            pass

    def updateInformation(self):
        # 这里写系统信息更新部分
        # TODO(已完成): 补充功能
        # 这里不需要更新系统信息，只需要在程序初始化更新一次，毕竟这玩意是常量
        # -----------------------------------------------------------------------------
        if self.audio.playerLayer.isRun and not self.audio.playerLayer.is_play_ended:
            self.localInfo.playStatus = PlayStatus.Play
        elif self.audio.playerLayer.file_path != "":
            if self.audio.playerLayer.audio_frame == 0:
                self.localInfo.playStatus = PlayStatus.Load
            elif self.audio.playerLayer.audio_frame >= self.audio.playerLayer.duration_frame:
                self.localInfo.playStatus = PlayStatus.End
            else:
                self.localInfo.playStatus = PlayStatus.Pause
        else:
            self.localInfo.playStatus = PlayStatus.Unknown
        self.localInfo.delay = self.delay
        self.localInfo.difference = self.difference
        if self.localInfo.playStatus != PlayStatus.Unknown:
            self.localInfo.benchmarkPlayingPosition = self.audio.get_position()
        else:
            self.localInfo.benchmarkPlayingPosition = 0
        self.localInfo.benchmarkTimestamp = self.get_server_timestamp()
        self.localInfo.uuid = self.identity
        self.sio.emit("Information", {"Identity": self.identity, "JData": self.localInfo.json()})

    #@sio.on("Information")
    def information(self, data):
        identity = data["Identity"]
        if "Except" in data.keys():
            if data["Except"] == self.identity:
                return
        if identity == self.identity or identity == "Broadcast":
            if "JData" in data.keys():
                json_str = data["JData"]
                item_changed = self.kernelInfo.update(json_str)
                if "DataModel.playStatus" in item_changed:
                    self.onPlayStatusChanged(self.kernelInfo.playStatus)
                if self.kernelInfo.command is not Command.Null:
                    self.onCommand(self.kernelInfo.command)

    #@sio.on("Time")
    def time(self, data):
        """
        计算同步信息
        :param data: dict
        :return: None
        """
        time_now = time.time()
        identity = data["Identity"]
        if "Except" in data.keys():
            if data["Except"] == self.identity:
                return
        if identity == self.identity:
            time_receive = data["TimeReceive"]
            # time_reply = data["TimeReply"]
            time_difference = (time_receive - self.time_send) - ((time_now - self.time_send) / 2)
            self.list_difference.append(time_difference)
            delay = time_now - self.time_send
            self.list_delay.append(delay)
            # deviation = (time_reply - time_now + delay) - time_difference
            if data["Times"] >= 5:
                self.difference = float(np.average(self.list_difference))
                self.delay = float(np.average(self.list_delay))
                self.sio.emit("Information",
                              {"Identity": self.identity, "Type": "Difference", "Difference": self.difference})
                self.sio.emit("Information",
                              {"Identity": self.identity, "Type": "Delay", "Delay": self.delay})
                return
            self.sio.emit("Time", {"Identity": self.identity, "Times": data["Times"] + 1})

    def update_operate_system_information(self):
        """
        提交操作系统信息
        :return: None
        """
        python_version = platform.python_version()
        host_name = platform.node()
        os_name = platform.platform()
        # cpu = platform.processor()
        architecture = platform.machine()
        system = platform.system()
        system = system if system != "Darwin" else "MacOS/OSX/Darwin"

        self.localInfo.system = system
        self.localInfo.name = host_name
        self.localInfo.system_name = os_name
        self.localInfo.architecture = architecture
        self.localInfo.pythonVersion = python_version

    def register(self):
        self.sio.emit("Register", {"Identity": self.identity})

    @staticmethod
    def runshell(command):
        with os.popen(command) as f:
            return f.read()

    def generate_id(self):
        system = platform.system()
        uuidStr = None
        if system == "Windows":
            results = self.runshell("wmic csproduct get uuid").split('\n')
            for result in results:
                reResult = re.search(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", result)
                if reResult is not None:
                    uuidStr = reResult.group(0)
        if system == "Linux":
            results = self.runshell("dmidecode").split('\n')
            for result in results:
                reResult = re.search(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", result)
                if reResult is not None:
                    uuidStr = reResult.group(0)
        if system == "Darwin":
            results = self.runshell("ioreg -c IOPlatformExpertDevice").split('\n')
            for result in results:
                reResult = re.search(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", result)
                if reResult is not None:
                    uuidStr = reResult.group(0)
        uuidStr = uuidStr if uuidStr is not None else str(uuid.uuid1())
        self.identity = uuidStr

    def time_redress(self):
        self.audio.loop = asyncio.get_event_loop()
        while self.isRun:
            self.list_delay = []
            self.list_difference = []
            self.time_send = time.time()
            self.sio.emit("Time", {"Identity": self.identity, "Times": 1})
            time.sleep(self.redress_frequency_time)

    def connect(self, url):
        self.sio.connect(url)
        self.isRun = True

    def bind(self):
        self.sio = socketio.Client()

        @self.sio.on("Time")
        def _time(data):
            self.time(data)

        @self.sio.on("Information")
        def information(data):
            self.information(data)

    def run(self):
        self.generate_id()
        self.register()
        self.update_operate_system_information()
        self.time_redress()
