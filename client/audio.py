import json
import math
import os
import ssl
import threading
import time
from pathlib import Path

import numpy as np
import pyaudio
import wget
from loguru import logger
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
    def __init__(self, cache_path=None):
        self.cache_path = "cache" if cache_path is None else cache_path
        self.playerLayer: PlayLayer = PlayLayer("")
        self.isPlaying = False

    def load(self, url, video_id):
        if self.playerLayer.file_path is not "":
            self.playerLayer.stop()
        self.isPlaying = False
        self._load(url, video_id)
        return self

    def _load(self, url, video_id):
        if not Path(self.cache_path).is_dir():
            os.mkdir(self.cache_path)
        path_json = os.path.join(self.cache_path, "cache.json")
        if not Path(path_json).is_file():
            file_write(path_json, json.dumps([]))
        caches = json.loads(file_read(path_json))
        isInCache = False
        for cache in caches:
            video_id_cache = cache["video_id"]
            if video_id_cache == video_id and Path(os.path.join(self.cache_path, f"{video_id_cache}.m4a")).is_file():
                isInCache = True
        if not isInCache:
            parallelDownload = ParallelDownload(maxThread=1000)
            parallelDownload.download(url, os.path.join(self.cache_path, f"{video_id}.m4a"), self.loop)
            caches.append({"video_id": video_id, "extension_name": "m4a"})
        file_write(path_json, json.dumps(caches))
        self.playerLayer.load_source(os.path.join(self.cache_path, f"{video_id}.m4a"))

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
        self.playerLayer.set_position(seconds)

    def get_position(self):
        return self.playerLayer.get_position()


class PlayLayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.benchmark_time = -1
        self.enable_benchmark = False
        self.audio_frame = -1
        self.isRun = False
        self.isPause = False
        self.thread = None
        self.source_array = None
        self.is_play_ended = False
        self.audio_frame_step = (1 / 44100)

    def load_source(self, file_path):
        self.file_path = ""
        self.audio_frame = 0
        self._set_audio_source(file_path)
        self._init_player()
        self.file_path = file_path

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
        self.is_play_ended = False
        logger.info(f"音频[{os.path.split(self.file_path)[-1]}]开始播放")
        if self.enable_benchmark:
            self.audio_frame += math.floor((time.time() - self.benchmark_time) / self.audio_frame_step)
            self.enable_benchmark = False
        while self.audio_frame < self.duration_frame and self.isRun:  # 循环，直到时间大于结束
            if self.enable_benchmark:
                self.audio_frame += math.floor((time.time() - self.benchmark_time) / self.audio_frame_step)
                self.enable_benchmark = False
            try:
                self.stream.write(self.source_array[self.audio_frame].tostring())
            except:
                logger.error("音频播放出错")
                break
            self.audio_frame += 1
        if not self.isPause:
            self.p.terminate()  # 关闭
            self._on_play_ended()
            logger.info(f"音频[{os.path.split(self.file_path)[-1]}]停止播放")
        else:
            logger.info(f"音频[{os.path.split(self.file_path)[-1]}]暂停播放")
            self.isPause = False
        self.is_play_ended = True

    def set_position(self, seconds: float):
        self.audio_frame = math.floor(seconds / self.audio_frame_step)

    def set_position_with_benchmark_customize(self, seconds: float, benchmark_time: float):
        """
        警告，调用此方法后必须立刻启动播放器，不然此方法不仅没有实际意义还将会导致下一次播放失败
        Warning, the player must be started immediately after calling this method,
         otherwise this method will not only have no practical meaning, but will also cause the next playback to fail
        :param benchmark_time:
        :param seconds:
        :return:
        """
        self.benchmark_time = benchmark_time
        self.set_position(seconds)
        self.enable_benchmark = True

    def set_position_with_benchmark(self, seconds: float):
        """
        警告，调用此方法后必须立刻启动播放器，不然此方法不仅没有实际意义还将会导致下一次播放失败
        Warning, the player must be started immediately after calling this method,
         otherwise this method will not only have no practical meaning, but will also cause the next playback to fail
        :param seconds:
        :return:
        """
        self.benchmark_time = time.time()
        self.set_position(seconds)
        self.enable_benchmark = True

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
        if self.thread is not None:
            self.thread.join()

    def reset(self):
        if self.is_play_ended:
            self._init_player()
            self.is_play_ended = False
