import json
import os
import re

from loguru import logger
from pytube import YouTube
from pytube.exceptions import RegexMatchError


def file_read(path, encoding='utf-8'):
    with open(path, encoding=encoding) as f:
        return f.read()


def file_write(path, data, encoding='utf-8'):
    with open(path, 'w', encoding=encoding) as f:
        f.write(data)


def getFileSize(filePath):
    filePath = str(filePath)
    fsize = os.path.getsize(filePath)
    fsize = fsize / float(1024 * 1024)
    return round(fsize, 4)


class Song:
    def __init__(self, path_dataset):
        self.path_dataset = path_dataset
        self.playlists = {}
        self.current_playlist = ""
        self.current_song = 0
        self.playback_progress = 0
        self.playback_progress_percentage = 0
        self.benchmark_timestamp = 0
        self.circle_mod = True

        status = self._checkDataset()
        if status == 1:
            logger.info(f"播放数据集不存在, 创建新的播放数据集, Path:[{self.path_dataset}]")
            self._createEmptyDataset()
        elif status == 2:
            logger.error(f"播放数据集已损坏, 请手动删除, Path:[{self.path_dataset}]")
            exit(0)
        elif status == 3:
            logger.error(f"播放数据集不是合法的json结构, 请检查后重启程序, Content:[{file_read(self.path_dataset)}]")
            exit(0)
        elif status == 4:
            logger.error(f"播放数据集结构错误, 请检查后重启程序, Content:[{file_read(self.path_dataset)}]")
            exit(0)

        self._read_music_list()

    def _read_music_list(self):
        data = json.loads(file_read(self.path_dataset))
        music_list = data["music_list"]
        self.current_playlist = data["current_playlist"]
        self.current_song = data["current_song"]
        for playlist in music_list:
            list_name = playlist['name']
            list_song = playlist['songs']
            self.playlists[list_name] = [{} for x in range(len(list_song))]
            logger.debug(f"  List '{list_name}' {{{len(list_song)}}} song")
            for song in list_song:
                index = song['id']
                url = song['url']
                music = self.load_music(url)
                self.playlists[list_name][index] = music
                logger.debug(f"    Music: [{music['title']}] Length: [{music['length']}s] Author: [{music['author']}]")
        logger.info(f"播放数据集读入, Path:[{self.path_dataset}] {getFileSize(self.path_dataset)} MB")
        logger.info(f"    一共{len(self.playlists.keys())}个播放列表")

    def _save_music_list(self):
        music_list = []
        for list_name in self.playlists.keys():
            playlist = []
            for i in range(len(self.playlists[list_name])):
                playlist.append({
                    "id": i,
                    "url": self.playlists[list_name][i]['link']
                })
            music_list.append({
                "name": list_name,
                "songs": playlist
            })
        data = {
            "music_list": music_list,
            "current_playlist": self.current_playlist,
            "current_song": self.current_song
        }
        file_write(self.path_dataset, json.dumps(data, sort_keys=True, indent=4, separators=(', ', ': ')))
        logger.info(f"播放数据集已保存, Path:[{self.path_dataset}] {getFileSize(self.path_dataset)} MB")

    def save(self):
        self._save_music_list()

    def _createEmptyDataset(self):
        data = {
            "music_list": [],
            "current_playlist": "",
            "current_song": 0
        }
        file_write(self.path_dataset, json.dumps(data))

    def _checkDataset(self):
        if not os.path.exists(self.path_dataset):
            return 1
        if not os.path.isfile(self.path_dataset):
            return 1
        content = None
        try:
            content = file_read(self.path_dataset)
        except Exception as e:
            logger.error(f"读取播放数据集出错, Path:[{self.path_dataset}]")
            logger.error(e)
            return 2
        data = None
        try:
            data = json.loads(content)
        except Exception as e:
            logger.error(f"解析播放数据集出错, Path:[{self.path_dataset}]")
            logger.error(e)
            return 3
        keys = data.keys()
        if "music_list" not in keys or "current_playlist" not in keys or "current_song" not in keys:
            return 4
        if type(data["music_list"]) != list or type(data["current_playlist"]) != str or type(
                data["current_song"]) != int:
            return 4
        if len(data["music_list"]) > 0:
            if "name" not in data["music_list"][0] or "songs" not in data["music_list"][0]:
                return 4
        return 0

    @staticmethod
    def load_music(url):
        yt = YouTube(url)
        streams = yt.streams
        list_audios = streams.filter(only_audio=True)
        list_audios = sorted(list_audios, key=lambda x: int(re.search("^[0-9]+", x.abr)[0]), reverse=True)[0]
        return {
            "youtube": yt,
            "link": url,
            "audio_link": yt.streams.get_audio_only().url,  # list_audios.url,
            "title": list_audios.title,
            "author": yt.author,
            "length": yt.length
        }

    def add_song(self, name_playlist, url):
        music = None
        try:
            music = self.load_music(url)
        except RegexMatchError as e:
            logger.error(f"加载歌曲失败, Url 非法:[{url}]")
            return False
        if music is None:
            return False
        if name_playlist not in self.playlists.keys():
            self.new_playlist(name_playlist, False)
        urls = [x["link"] for x in self.playlists[name_playlist]]
        if url in urls:
            logger.info(f"歌曲已存在, Url:[{url}]")
            return True
        self.playlists[name_playlist].append(music)
        index = len(self.playlists[name_playlist]) - 1
        logger.debug(
            f"歌曲[{music['title']}]已加入播放清单[{name_playlist}], 一共{len(self.playlists[name_playlist])}首歌, id: {index}")
        self._save_music_list()
        return index

    def remove_song(self, name_playlist, index):
        if name_playlist not in self.playlists.keys():
            logger.error(f"播放列表不存在:[{name_playlist}]")
            raise PlaylistNameNotExistError(name_playlist)
            return False
        if index >= len(self.playlists[name_playlist]):
            logger.error(f"歌曲索引不存在:[{index}]")
            raise SongIndexNotExistError(index)
            return False
        del self.playlists[name_playlist][index]
        logger.debug(f"歌曲[{index}]已从播放清单[{name_playlist}]中删除, 清单内一共{len(self.playlists[name_playlist])}首歌")
        self._save_music_list()
        return True

    def new_playlist(self, name_playlist, enableSave=True):
        if name_playlist in self.playlists.keys():
            logger.error(f"播放列表已存在:[{name_playlist}]")
            raise PlaylistNameExistError(name_playlist)
            return False
        self.playlists[name_playlist] = []
        logger.debug(f"播放列表已创建[{name_playlist}]")
        if enableSave:
            self._save_music_list()
        return True

    def remove_playlist(self, name_playlist):
        if name_playlist not in self.playlists.keys():
            logger.error(f"播放列表不存在:[{name_playlist}]")
            raise PlaylistNameNotExistError(name_playlist)
            return False
        num_playlists = len(self.playlists[name_playlist])
        del self.playlists[name_playlist]
        logger.debug(f"播放列表已删除[{name_playlist}], 一共[{num_playlists}]首歌")
        self._save_music_list()
        True

    def get_current_playlist(self):
        return self.playlists[self.current_playlist]

    def current(self) -> dict:
        return self.get_current_playlist()[self.current_song]

    def next(self):
        if self.current_song + 1 >= len(self.get_current_playlist()):
            self.current_song = -1
        self.current_song += 1
        return self.current()

    def back(self):
        if self.current_song - 1 < 0:
            self.current_song = len(self.get_current_playlist())
        self.current_song -= 1
        return self.current()

    def setcurrent(self, index):
        self.current_song = index
        self.playback_progress = 0
        self.playback_progress_percentage = 0
        self.benchmark_timestamp = 0


class PlaylistNameExistError(Exception):
    def __init__(self, playlist_name):
        super().__init__(f"播放列表[{playlist_name}]已存在")


class PlaylistNameNotExistError(Exception):
    def __init__(self, playlist_name):
        super().__init__(f"播放列表[{playlist_name}]不存在")


class SongIndexNotExistError(Exception):
    def __init__(self, song_index):
        super().__init__(f"歌曲索引[{song_index}]不存在")
