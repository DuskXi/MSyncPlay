import threading
import time

import numpy as np
from flask import Flask, render_template
from flask_socketio import SocketIO
from loguru import logger

from link import LinkManager
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
        self.linkManager = None
        self.list_music = []
        self.timeout = 60
        self.offline_threshold = 20
        self.song = None
        self.benchmark_device = None

    def run(self):
        self.socketio.run(self.app, host=self.host, port=self.port)

    def load_music(self, path_dataset):
        self.song = Song(path_dataset)

    def update_system_information(self, identity, data):
        self.list_information[identity]["PythonVersion"] = data["PythonVersion"]
        self.list_information[identity]["HostName"] = data["HostName"]
        self.list_information[identity]["OS"] = data["OS"]
        self.list_information[identity]["CPU"] = data["CPU"]
        self.list_information[identity]["Architecture"] = data["Architecture"]
        self.list_information[identity]["System"] = data["System"]
        self.list_information[identity]["enabled"] = True
        self.list_information[identity]["UpdateTime"] = time.time()

    def update_uuid(self, identity, newid):
        self.list_information[newid] = self.list_information[identity]
        self.socketio.emit("UUIDUpdated", {"Identity": identity})

    def update_other_property(self, identity, _type, value):
        self.list_information[identity][_type] = value
        self.list_information[identity]["UpdateTime"] = time.time()

    def status_update(self, data):
        identity = data['Identity']
        if data["StatusType"] == "LoadingStatus":
            self.list_information[identity]["Loaded"] = data["LoadingStatus"]
        if data["StatusType"] == "PlayingStartTime":
            self.list_information[identity]["PlayingStartTime"] = data["PlayingStartTime"]
            self.list_information[identity]["isPlaying"] = True
        if data["StatusType"] == "PlayingStatus":
            self.list_information[identity]["isPlaying"] = data["PlayingStatus"]
            self.song.playback_progress = 0
            # if identity == self.benchmark_device and self.song.circle_mod and self.song.current_song + 1 != len(
            #         self.song.get_current_playlist()):
            #     self.song.next()
            #     self.play_music()

    def play_music(self, index=None):
        if self.list_information[self.benchmark_device]["isPlaying"] and index is None:
            self.socketio.emit("Command", {"Identity": "Broadcast", "Command": "Pause"})
            for device in self.list_information.values():
                device["isPlaying"] = False
        else:
            if index is not None:
                self.song.setcurrent(index)
            if self.song.playback_progress == 0:
                self.socketio.emit("Command", {
                    "Identity": "Broadcast",
                    "Command": "Load",
                    "url": self.song.current()["audio_link"],
                    "youtube_id": self.song.current()["youtube"].video_id
                })
            threading.Thread(target=self.waiting_thread).start()

    def check_heartbeat_package(self):
        for device in self.list_information.values():
            if device["UpdateTime"] + self.offline_threshold < time.time():
                device["live"] = False
                logger.info("Device {} offline".format(device["Identity"]))

    def update_position(self, position, timestamp):
        self.song.playback_progress = position
        self.song.playback_progress_percentage = position / self.song.current()['length']
        self.song.benchmark_timestamp = timestamp

    #@socketio.on("Information")
    def information(self, data):
        identity = data["Identity"]
        if data["Type"] == "SystemInformation":
            self.update_system_information(identity, data)
        elif data["Type"] == "UUIDUpdate":
            self.update_uuid(identity, data['NewID'])
        elif data["Type"] == "Position":
            self.update_position(data["Position"], data["Timestamp"])
        else:
            self.update_other_property(identity, data["Type"], data[data["Type"]])

    #@socketio.on("Register")
    def register(self, data):
        identity = data["Identity"]
        self.list_information[identity] = {"Identity": identity, "Loaded": False, "isPlaying": False, "live": True}
        if len(self.list_information) == 1:
            self.benchmark_device = identity
        self.distribution_music_list()

    # @socketio.on("Time")
    def time(self, data):
        time_receive = time.time()
        identity = data["Identity"]
        self.socketio.emit('Time', {"Identity": identity, "TimeReceive": time_receive, "TimeReply": time.time(),
                                    "Times": data["Times"]}, broadcast=False)

    #@socketio.on("web")
    def web(self, data):
        # identity = data["Identity"]
        if "Type" in data.keys():
            if data["Type"] == "RequestInformationUpdate":
                if self.benchmark_device is not None:
                    if self.list_information[self.benchmark_device]["isPlaying"]:
                        self.socketio.emit("Information",
                                           {"Identity": self.benchmark_device,
                                            "Type": "Collection",
                                            "CollectionItems": ["Position"]})
                self.page_update()
            if data["Type"] == "ChangeInformation":
                for item in data["data"]:
                    self.list_information[item["uuid"]]["enabled"] = item["enabled"]
                self.page_update()
            if data["Type"] == "BenchmarkDevice":
                self.benchmark_device = data["uuid"]
            if data["Type"] == "Play":
                self.play_music(data["id"] if "id" in data.keys() else None)
            if data["Type"] == "Pause":
                self.socketio.emit("Command", {"Identity": "Broadcast", "Command": "Pause"})
                for device in self.list_information:
                    device["isPlaying"] = False
            if data["Type"] == "Redress":
                self.socketio.emit("Command",
                                   {"Identity": "Broadcast",
                                    "Except": self.benchmark_device,
                                    "Command": "Redress",
                                    "Position": self.song.playback_progress,
                                    "Timestamp": self.song.benchmark_timestamp})

    def waiting_thread(self):
        start = time.time()
        while time.time() - start <= self.timeout:
            result = [x["Loaded"] for x in self.list_information.values()]
            if False not in result:
                maxDifference = np.max([abs(x["Difference"]) for x in self.list_information.values()])
                maxDelay = np.max([x["Delay"] for x in self.list_information.values()])
                self.socketio.emit("Command",
                                   {"Identity": "Broadcast",
                                    "Command": "Play",
                                    "Timestamp": time.time() + (maxDifference + (maxDelay * 2))},
                                   broadcast=True)
                break
            time.sleep(0.1)

    def page_update(self):
        devices = []
        for identity in self.list_information.keys():
            if not self.list_information[identity]["live"]:
                continue
            data = {
                "id": identity,
                "name": self.list_information[identity]["HostName"],
                "system": self.list_information[identity]["OS"],
                "pythonVersion": self.list_information[identity]["PythonVersion"],
                "uuid": self.list_information[identity]["Identity"],
                "enabled": self.list_information[identity]["enabled"],
                "updateTime": self.list_information[identity]["UpdateTime"],
                "difference": self.list_information[identity]["Difference"],
                "delay": self.list_information[identity]["Delay"],
                "benchmark_device": (self.list_information[identity]["Identity"] == self.benchmark_device)
            }
            if self.list_information[identity]["System"] == "Windows":
                data["icon"] = "bi bi-windows"
            elif self.list_information[identity]["System"] == "Linux":
                data["icon"] = "fab fa-linux"
            elif self.list_information[identity]["System"] == "MacOS/OSX/Darwin" or "Mac" in \
                    self.list_information[identity]["System"]:
                data["icon"] = "bi bi-apple"
            else:
                data["icon"] = "bi bi-pc-display"
            devices.append(data)
        self.socketio.emit("web", {"Type": "InformationUpdate", "devices": devices})

        self.socketio.emit("web", {"Type": "InformationUpdate",
                                   "progress": {
                                       "id": self.song.current_song,
                                       "percentage": self.song.playback_progress_percentage}})

        music = []
        current_playlist = self.song.get_current_playlist()
        current_song_index = self.song.current_song
        for i in range(len(current_playlist)):
            music.append({"id": i, "name": current_playlist[i]['title'], "singer": current_playlist[i]['author'],
                          "timeLong": self.song.playback_progress if i == current_song_index else
                          current_playlist[i][
                              'length'], "playing": (i == current_song_index)})
        self.socketio.emit("web", {"Type": "InformationUpdate", "musics": music})

        self.socketio.emit("web",
                           {"Type": "InformationUpdate",
                            "playlists": [x for x in self.song.playlists.keys()],
                            "list_active": self.song.current_playlist,
                            "play_status": self.list_information[self.benchmark_device][
                                "isPlaying"] if self.benchmark_device is not None else False})

    def index(self):
        return render_template('testIndex.html')

    def distribution_music_list(self):
        data = []
        for music in self.list_music:
            data.append(music["url"])
        self.socketio.emit("Information", {"Identity": "Broadcast", "Type": "Url", "Urls": data})

    @staticmethod
    def secondsToString(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)

    def bind(self):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        @self.app.route('/')
        @self.app.route('/index')
        def index():
            self.index()

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

        @self.socketio.on("StatusUpdate")
        def status_update(data):
            self.status_update(data)
