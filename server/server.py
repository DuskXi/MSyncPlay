import random
import threading
import time
from typing import Dict

from flask import Flask, render_template, render_template_string
from flask_socketio import SocketIO
from loguru import logger

from datamodel import *
from song import Song


def file_read(path, encoding='utf-8'):
    with open(path, 'r', encoding=encoding) as f:
        return f.read()


class Server:
    def __init__(self, host, port: int):
        self.app = None
        self.socketio = None
        self.host = host
        self.port = port
        self.list_information = {}
        self.timeout = 60
        self.offline_threshold = 20
        # self.song: Song = None
        self.music_continue = False
        self.benchmark_device = None
        self.list_clients: Dict[str, ClientInfoDataset] = {}
        self.isRun = True
        self.updateFrequency = 1
        self.playMode = PlayMode.ListLoop
        self._thread_information_update = threading.Thread(target=self.thread_information_update)
        self._thread_information_update.start()

    def run(self):
        self.socketio.run(self.app, host=self.host, port=self.port)

    def load_music(self, path_dataset):
        self.song: Song = Song(path_dataset)

    def play_music(self, index=None):
        if index is None:
            self.issueCommand(Command.Pause)
        else:
            self.song.setcurrent(index)
            self.issueCommand(Command.Load)
            threading.Thread(target=self.waiting_thread).start()

    def waiting_thread(self, directStart=False):
        start = time.time()
        while time.time() - start <= self.timeout:
            result = [x.playStatus == PlayStatus.Load for x in self.list_clients.values()]
            if False not in result or directStart:
                self.issueCommand(Command.Play)
                logger.info(f"全部设备加载完毕, 开始播放" if not directStart else "继续播放")
                self.music_continue = False
                break
            time.sleep(0.1)

    def check_heartbeat_package(self):
        for device in self.list_information.values():
            if device["UpdateTime"] + self.offline_threshold < time.time():
                device["live"] = False
                logger.info("Device {} offline".format(device["Identity"]))

    def play_status_check(self):
        if self.list_clients[self.benchmark_device].playStatus == PlayStatus.End and not self.music_continue:
            current_id = self.song.current_song
            length_list = len(self.song.get_current_playlist())
            next_song = -1
            if self.playMode == PlayMode.ListLoop:
                next_song = current_id + 1 if current_id + 1 < length_list else 0
            if self.playMode == PlayMode.Random:
                next_song = random.randint(0, length_list - 1)
            if self.playMode == PlayMode.Single:
                next_song = current_id
            if self.playMode == PlayMode.List:
                next_song = current_id + 1 if current_id + 1 < length_list else -1

            if 0 <= next_song < length_list:
                self.play_music(next_song)
                self.music_continue = True

    def issueCommand(self, command, identity="Broadcast", benchmarkPlayingPosition=None):
        """
        下发指令
        :param benchmarkPlayingPosition:
        :param command:
        :param identity:
        :return:
        """
        if len(self.list_clients.keys()) < 0:
            return
        if self.benchmark_device is None:
            self.benchmark_device = list(self.list_clients.keys())[0]
        if command == Command.Play:
            differences = [abs(x.difference) for x in self.list_clients.values()]
            benchmarkTimestamp = time.time() + max(differences)
            for key in self.list_clients.keys():
                self.list_clients[key].benchmarkTimestamp = benchmarkTimestamp
            self.sendDataUpdate(identity, command)
        if command == Command.Redress:
            self.sendDataUpdate(identity, command, Except=self.benchmark_device)

        if command == Command.Load:
            self.sendDataUpdate(identity, command)
        if command == Command.Pause:
            self.sendDataUpdate(identity, command)
        if command == Command.Stop:
            self.sendDataUpdate(identity, command)
        if command == Command.InformationCollection:
            self.sendDataUpdate(identity, command)
        if command == Command.SetPosition:
            self.sendDataUpdate(identity, command, benchmarkPlayingPosition)

        # 指令位复位

    def sendDataUpdate(self, identity: str, command=Command.Null, benchmarkPlayingPosition=None, **kwargs):
        """
        发送数据更新
        :param benchmarkPlayingPosition:
        :param command:
        :param identity:
        :param kwargs:
        :return:
        """
        data = {"Identity": identity, "JData": self.generateData(command, benchmarkPlayingPosition)}
        for key, value in kwargs.items():
            if key in ["Except"]:
                data[key] = value
        self.socketio.emit("Information", data)

    def generateData(self, command, benchmarkPlayingPosition=None):
        """
        生成要传输到播放设备的数据集
        :return:
        """
        data = DataModel()
        data.url = self.song.current()["audio_link"]
        data.command = command
        data.youtubeId = self.song.current()["youtube"].video_id
        data.playStatus = self.list_clients[self.benchmark_device].playStatus
        data.benchmarkDevice = self.benchmark_device
        if benchmarkPlayingPosition is not None:
            self.list_clients[self.benchmark_device].benchmarkTimestamp = time.time()
            self.list_clients[self.benchmark_device].benchmarkPlayingPosition = benchmarkPlayingPosition
        data.benchmarkTimestamp = self.list_clients[self.benchmark_device].benchmarkTimestamp
        data.benchmarkPlayingPosition = self.list_clients[self.benchmark_device].benchmarkPlayingPosition
        return data.json()

    def requestDataUpdate(self, identity: str):
        self.sendDataUpdate(identity, Command.InformationCollection)

    def information(self, data):
        identity = data["Identity"]
        if "JData" in data.keys():
            if identity in self.list_clients.keys():
                json_str = data["JData"]
                self.list_clients[identity].update(json_str)
                self.list_clients[identity].last_update_time = time.time()
                if identity == self.benchmark_device:
                    self.play_status_check()

    def register(self, data):
        identity = data["Identity"]
        self.list_clients[identity] = ClientInfoDataset()
        self.list_clients[identity].uuid = identity
        if len(self.list_clients.keys()) == 1:
            self.benchmark_device = identity
        self.requestDataUpdate(identity)

    def time(self, data):
        time_receive = time.time()
        identity = data["Identity"]
        self.socketio.emit('Time', {"Identity": identity, "TimeReceive": time_receive, "TimeReply": time.time(),
                                    "Times": data["Times"]}, broadcast=False)

    def web(self, data):
        # identity = data["Identity"]
        if "Type" in data.keys():
            if data["Type"] == "RequestInformationUpdate":
                self.page_update()
            if data["Type"] == "ChangeInformation":
                for item in data["data"]:
                    self.list_clients[item["uuid"]].enabled = item["enabled"]
                self.page_update()
            if data["Type"] == "BenchmarkDevice":
                self.benchmark_device = data["uuid"]
            if data["Type"] == "Play":
                self.play_music(data["id"] if "id" in data.keys() else None)
            if data["Type"] == "Pause":
                self.issueCommand(Command.Pause)
            if data["Type"] == "Redress":
                self.issueCommand(Command.Redress)
            if data["Type"] == "SetPosition":
                self.issueCommand(Command.SetPosition,
                                  benchmarkPlayingPosition=data["progress"] * self.song.current()['length'])
            if data["Type"] == "SetPlayMode":
                self.playMode = PlayMode(data["mode"])
                logger.info("PlayMode: " + str(self.playMode))
            if data["Type"] == "ChangePlayList":
                self.song.current_playlist = data["playlist"]
                if data["playlist"] not in self.song.list_loaded:
                    self.song.start_load_music_list(data["playlist"])
                if self.list_clients[self.benchmark_device].playStatus == PlayStatus.Playing:
                    self.issueCommand(Command.Stop)

    def page_update(self):
        devices = []
        for identity in self.list_clients.keys():
            # TODO: 断线功能
            # if not self.list_information[identity]["live"]:
            #     continue
            data = {
                "id": identity,
                "name": self.list_clients[identity].name,
                "system": self.list_clients[identity].system,
                "pythonVersion": self.list_clients[identity].pythonVersion,
                "uuid": self.list_clients[identity].uuid,
                "enabled": self.list_clients[identity].enabled,
                "updateTime": self.list_clients[identity].last_update_time,
                "difference": self.list_clients[identity].difference,
                "delay": self.list_clients[identity].delay,
                "benchmark_device": self.list_clients[identity].uuid == self.benchmark_device
            }
            if self.list_clients[identity].system == "Windows":
                data["icon"] = "bi bi-windows"
            elif self.list_clients[identity].system == "Linux":
                data["icon"] = "fab fa-linux"
            elif self.list_clients[identity].system == "MacOS/OSX/Darwin" or "Mac" in \
                    self.list_information[identity]["System"]:
                data["icon"] = "bi bi-apple"
            else:
                data["icon"] = "bi bi-pc-display"
            devices.append(data)
        self.socketio.emit("web", {"Type": "InformationUpdate", "devices": devices})

        self.socketio.emit("web", {"Type": "InformationUpdate",
                                   "progress": {
                                       "id": self.song.current_song,
                                       "percentage":
                                           self.list_clients[self.benchmark_device].benchmarkPlayingPosition /
                                           self.song.current()['length'] if self.benchmark_device is not None else 0}})

        musics = []
        current_playlist = self.song.get_current_playlist()
        current_song_index = self.song.current_song
        for i in range(len(current_playlist)):
            if len(current_playlist[i]) > 0:
                music = {"id": i, "name": current_playlist[i]['title'],
                         "singer": current_playlist[i]['author'],
                         "playing": (i == current_song_index),
                         "maxTimeLong": current_playlist[i]['length'],
                         "img": current_playlist[i]['thumbnail_url']}
                if self.benchmark_device is not None and i == current_song_index:
                    if self.list_clients[self.benchmark_device].playStatus == PlayStatus.Play or \
                            self.list_clients[self.benchmark_device].playStatus == PlayStatus.Pause:
                        music["timeLong"] = self.list_clients[self.benchmark_device].benchmarkPlayingPosition
                    else:
                        music["timeLong"] = current_playlist[i]['length']
                else:
                    music["timeLong"] = current_playlist[i]['length']
                musics.append(music)
        self.socketio.emit("web", {"Type": "InformationUpdate", "musics": musics})

        self.socketio.emit("web",
                           {"Type": "InformationUpdate",
                            "playlists": [x for x in self.song.playlists.keys()],
                            "list_active": self.song.current_playlist,
                            "play_status": self.list_clients[self.benchmark_device].playStatus.value
                            if self.benchmark_device is not None
                            else False,
                            "play_mode": self.playMode.value,
                            "loading": self.song.isLoading,
                            "loading_progress": round(
                                self.song.loading_progress / self.song.num_loading_task_music * 100, 2)
                            if self.song.num_loading_task_music != 0 else 0})

    def thread_information_update(self):
        while self.isRun:
            if len(self.list_clients.keys()) > 0 and self.benchmark_device is not None:
                # for key in self.list_clients.keys():
                #     if time.time() - self.list_clients[key].last_update_time >= self.offline_threshold:
                #         del self.list_clients[key]
                #         logger.info(f"Device {key} is offline")

                self.issueCommand(Command.InformationCollection)
            time.sleep(self.updateFrequency)

    def index(self):
        html = str(file_read('templates/index.html'))
        return html

    @staticmethod
    def secondsToString(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)

    def bind(self):
        self.app = Flask(__name__, static_folder="templates")
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        @self.app.route('/')
        @self.app.route('/index')
        def index():
            return self.index()

        @self.socketio.on("web")
        def web(data):
            self.web(data)

        @self.socketio.on("Time")
        def _time(data):
            self.time(data)

        @self.socketio.on("Register")
        def register(data):
            self.register(data)

        @self.socketio.on("Information")
        def information(data):
            self.information(data)
