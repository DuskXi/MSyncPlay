import json
import math
import os
import threading
import time

import numpy as np
import pyaudio
import wget
import ssl
import vlc
from loguru import logger
from moviepy.audio.io.AudioFileClip import AudioFileClip
from numba import jit
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment
from paralleldownload import ParallelDownload

ssl._create_default_https_context = ssl._create_unverified_context


def file_write(filename, content, encoding='utf-8'):
    with open(filename, 'w', encoding=encoding) as f:
        f.write(content)


def file_read(filename, encoding='utf-8'):
    with open(filename, 'r', encoding=encoding) as f:
        return f.read()


class Audio:
    def __init__(self, url, video_id, cache_path=None):
        self.cache_path = "cache" if cache_path is None else cache_path
        self.playerLayer = None
        self._load(url, video_id)
        self.isPlaying = False

    def update(self, url, video_id):
        self.playerLayer.stop()
        self._load(url, video_id)
        return self

    @staticmethod
    def isFileExist(path):
        return os.path.isfile(path)

    def _load(self, url, video_id):
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
        path_json = os.path.join(self.cache_path, "cache.json")
        if not os.path.exists(path_json):
            file_write(path_json, json.dumps([]))
        caches = json.loads(file_read(path_json))
        isInCache = False
        for cache in caches:
            video_id_cache = cache["video_id"]
            extension_name = cache["extension_name"]
            if video_id_cache == video_id:
                isInCache = True
        if not isInCache:
            parallelDownload = ParallelDownload(maxThread=100)
            parallelDownload.download(url, os.path.join(self.cache_path, f"{video_id}.m4a"))
            caches.append({"video_id": video_id, "extension_name": "m4a"})
        file_write(path_json, json.dumps(caches))
        self.playerLayer = PlayLayer(os.path.join(self.cache_path, f"{video_id}.m4a"))
        # self.playerLayer = PlayLayer(url)

    @staticmethod
    def _download(url, name):
        wget.download(url, name)

    def onPlayEnded(self, callback):
        self.playerLayer.bindEventOnPlayEnded(callback)

    def play(self):
        self.isPlaying = True
        self.playerLayer.play()

    def pause(self):
        self.playerLayer.pause()
        self.isPlaying = False

    def set_position(self, seconds: float):
        """

        :param seconds:
        :return:
        """
        self.playerLayer.set_position(seconds)

    def get_position(self):
        return self.playerLayer.get_position()


class PlayLayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.start = -1
        self.benchmark_time = -1
        self.progress_increment = 0
        self.audio_frame = -1
        self.isRun = False
        self.isPause = False
        self.thread = None
        self.source_array = None
        self.is_play_ended = False
        self._set_audio_source(self.file_path)
        self._init_player()

    def _init_player(self):
        self.p = pyaudio.PyAudio()  # 创建音频播放器
        self.stream = self.p.open(format=pyaudio.paInt16, channels=2, rate=self.audio_fps, output=True)  # 创建音频流

    def _set_audio_source(self, path):
        sound = AudioSegment.from_file(path)
        array = np.array(sound.get_array_of_samples())
        array = array.reshape((-1, sound.channels))
        self.source_array = array
        self.audio_fps = sound.frame_rate
        self.audio_frame_step = (1 / sound.frame_rate)
        self.duration_frame = sound.frame_count()

    def thread_play(self):
        start = time.time()  # 启动播放流
        # self.audio_frame = 0
        print(f"{(time.time() - start) * 1000}ms")
        while self.audio_frame < self.duration_frame and self.isRun:  # 循环，直到时间大于结束
            self.stream.write(self.source_array[self.audio_frame].tostring())
            self.audio_frame += 1
        if not self.isPause:
            self.p.terminate()  # 关闭
            self._on_play_ended()
            logger.info(f"音频[{os.path.split(self.file_path)[-1]}]停止播放")
        else:
            logger.info(f"音频[{os.path.split(self.file_path)[-1]}]暂停播放")
            self.isPause = False

    def set_position(self, seconds: float):
        self.audio_frame = math.floor(seconds / self.audio_frame_step)

    def get_position(self):
        return self.audio_frame * self.audio_frame_step

    def _on_play_ended(self):
        pass

    def bindEventOnPlayEnded(self, func):
        self._on_play_ended = func
        self.is_play_ended = True

    def _start(self):
        self.isRun = True
        self.thread = threading.Thread(target=self.thread_play)
        self.thread.start()

    def play(self):
        self._start()

    def pause(self):
        if not self.isPause:
            if self.isRun:
                self.isPause = True
                self.isRun = False
        else:
            self._start()

    def stop(self):
        self.isRun = False
        self.thread.join()

    def reset(self):
        if self.is_play_ended:
            self._init_player()
