from pytube import YouTube


class Url:
    def __init__(self, url):
        self.url = url
        self.site = None
        self.load()

    def load(self):
        self.site = YouTube(self.url)

    def get_url(self):
        urls = self.site.streams.filter(only_audio=True)
        return urls[len(urls) - 1].url
