import os
import platform
import re
import time
import uuid

import numpy as np
import socketio
from loguru import logger

from audio import Audio


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
        self.audio = None
        self.sio = None

    def load_music(self, url, youtube_id):
        start_time = time.time()
        self.audio = Audio(url, youtube_id) if self.audio is None else self.audio.update(url, youtube_id)
        logger.info(
            f"歌曲加载完毕, 耗时: {(time.time() - start_time) * 1000} ms [video_id]: {youtube_id}")
        self.sio.emit("StatusUpdate",
                      {"Identity": self.identity, "StatusType": "LoadingStatus", "LoadingStatus": True})

    def play_music(self, start_time):
        while True:
            time.sleep(0.0001)
            if time.time() >= start_time - self.difference:
                break
        play_start_time = time.time() + self.difference
        self.audio.play()
        self.audio.onPlayEnded(self.onPlayEnded)
        logger.info(f"开始播放...")
        self.sio.emit("StatusUpdate", {"Identity": self.identity, "StatusType": "PlayingStartTime",
                                       "PlayingStartTime": play_start_time})

    def pause_music(self):
        if self.audio.isPlaying:
            self.audio.pause()

    def reBuildUUID(self):
        new_uuid = str(uuid.uuid4())
        self.sio.emit("Information", {"Identity": self.identity, "Type": "UUIDUpdate", "NewID": new_uuid})
        self.identity = new_uuid

    def onPlayEnded(self):
        self.audio.isPlaying = False
        self.sio.emit("StatusUpdate",
                      {"Identity": self.identity, "StatusType": "PlayingStatus", "PlayingStatus": False})

    def upload_Position(self):
        self.sio.emit("Information", {"Identity": self.identity,
                                      "Type": "Position",
                                      "Position": self.audio.get_position(),
                                      "Timestamp": self.get_server_timestamp()})

    temp_array = []

    def redress_music(self, position, timestamp):
        self.temp_array.append(
            self.audio.playerLayer.get_position() - (position + time.time() - (timestamp - self.difference)))
        logger.info(f"直接差: {self.audio.playerLayer.get_position() - position}")
        logger.info(
            f"修正差: {self.audio.playerLayer.get_position() - (position + time.time() - (timestamp - self.difference))}")
        logger.info(f"样本数: {len(self.temp_array)}, 样本标准差: {np.std(self.temp_array, ddof=1)}")
        logger.info(f"平均值: {np.average(self.temp_array)}")
        # 1.1290712900294224

        self.audio.playerLayer.stop()
        self.audio.playerLayer.reset()
        self.audio.playerLayer.set_position_with_benchmark(
            position + (-0.1) + time.time() - (timestamp - self.difference))
        self.audio.playerLayer.play()
        # logger.info(f"矫正完毕, 时间设为:{int(position + ((self.get_server_timestamp() - timestamp) * 1000))}"
        #             f"时间增量: {((self.get_server_timestamp() - timestamp) * 1000)}, "
        #             f"现有差: {int(position + ((self.get_server_timestamp() - timestamp) * 1000)) - self.audio.get_position()}")
        # self.audio.set_position(int(position + (self.get_server_timestamp() - timestamp)))

    def get_server_timestamp(self):
        return time.time() - self.difference

    def convert_server_timestamp_to_local(self, timestamp):
        return timestamp + self.difference

    #@sio.on("Command")
    def command(self, data):
        identity = data["Identity"]
        # if "Except" in data.keys():
        #     if data["Except"] == self.identity:
        #         return
        if identity == self.identity or identity == "Broadcast":
            # 加载音乐
            if data["Command"] == "Load":
                self.load_music(data["url"], data["youtube_id"])
            # 播放
            if data["Command"] == "Play":
                self.play_music(data["Timestamp"])
            # 暂停
            if data["Command"] == "Pause":
                self.pause_music()
            # 设置播放位置
            if data["Command"] == "SetPosition":
                self.audio.setPosition(data["Position"])
            if data["Command"] == "ReBuildUUID":
                self.reBuildUUID()
            if data["Command"] == "Redress":
                self.redress_music(data["Position"], data["Timestamp"])

    #@sio.on("Information")
    def information(self, data):
        identity = data["Identity"]
        if "Except" in data.keys():
            if data["Except"] == self.identity:
                return
        if identity == self.identity or identity == "Broadcast":
            # 更新歌曲列表
            if data["Type"] == "Url":
                logger.warning("歌曲列表已更新")
                logger.info(self.urls)
            # 收取信息
            if data["Type"] == "Collection":
                for element in data["CollectionItems"]:
                    # 当前播放位置信息
                    if element == "Position":
                        self.upload_Position()
            if data["Type"] == "UUIDUpdated":
                self.update_operate_system_information()

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
            time_reply = data["TimeReply"]
            time_difference = (time_receive - self.time_send) - ((time_now - self.time_send) / 2)
            self.list_difference.append(time_difference)
            delay = time_now - self.time_send
            self.list_delay.append(delay)
            deviation = (time_reply - time_now + delay) - time_difference
            if data["Times"] >= 5:
                self.difference = np.average(self.list_difference)
                self.delay = np.average(self.list_delay)
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
        cpu = platform.processor()
        architecture = platform.machine()
        system = platform.system()
        system = system if system != "Darwin" else "MacOS/OSX/Darwin"
        self.sio.emit("Information", {
            "Identity": self.identity,
            "Type": "SystemInformation",
            "PythonVersion": python_version,
            "HostName": host_name,
            "OS": os_name,
            "CPU": cpu,
            "Architecture": architecture,
            "System": system
        })

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

        @self.sio.on("Command")
        def command(data):
            self.command(data)

    def run(self):
        self.generate_id()
        self.register()
        self.update_operate_system_information()
        self.time_redress()
