import re

import pytube


class LinkManager:
    def __init__(self):
        self.list_youtube_link = []
        self.list_music = []

    def add_link(self, url):
        self.list_youtube_link.append(pytube.YouTube(url))

    def pull_link(self):
        for link in self.list_youtube_link:
            list_audio = list(link.streams.filter(only_audio=True))
            list_audio = list(sorted(list_audio, key=lambda x: int(re.search("^[0-9]+", x.abr)[0]), reverse=True))
            self.list_music.append(list_audio[0])
            self.list_music[len(self.list_music) - 1].author = link.author
            self.list_music[len(self.list_music) - 1].length = link.length
