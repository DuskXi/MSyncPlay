import asyncio
import math
import threading
import time

import progressbar
import requests


class ParallelDownload:
    def __init__(self, maxThread=750, enablePrint=True):
        self.maxThread = maxThread
        self.lengthBytesDownloaded = 0
        self.lastLengthBytesDownloaded = 0
        self.enablePrint = enablePrint
        self.fileSize = 0
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"}

    async def _threadDownload(self, url, chunkId, chunkStart, chunkEnd):
        headers = {"Range": f"bytes={chunkStart}-{chunkEnd}"}
        response = requests.get(url, headers={**headers, **self.headers}, stream=True)
        arrayBytes = b''
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                arrayBytes += chunk
                self.lengthBytesDownloaded += len(chunk)
        return chunkId, arrayBytes

    async def _startDownload(self, url, fileName, numChunks, chunkSize, lastChunkSize):
        data = []
        for i in range(numChunks - 1):
            data.append((i, chunkSize * i, (chunkSize * (i + 1)) - 1))
        data.append((numChunks - 1, chunkSize * (numChunks - 1), (chunkSize * (numChunks - 1)) + lastChunkSize - 1))
        tasks = [self._threadDownload(url, index, start, end) for index, start, end in data]
        results = await asyncio.gather(*tasks)
        with(open(fileName, 'wb')) as f:
            for chunkId, arrayBytes in results:
                f.write(arrayBytes)

    def calculateChunkSize(self, fileSize):
        minChunkSize = 1024 * 1024  # 1KB
        stepIncreaseSize = 1024
        chunkSize = minChunkSize
        numChunks = math.ceil(fileSize / chunkSize)
        while numChunks > self.maxThread:
            chunkSize += stepIncreaseSize
            numChunks = math.ceil(fileSize / chunkSize)
        return numChunks, chunkSize, fileSize - ((numChunks - 1) * chunkSize)

    @staticmethod
    def _lengthBytesToString(lengthBytes):
        if lengthBytes < 1024:
            return f"{lengthBytes}Byte"
        elif lengthBytes < 1024 * 1024:
            return f"{round(lengthBytes / 1024, 2)}KB"
        elif lengthBytes < 1024 * 1024 * 1024:
            return f"{round(lengthBytes / (1024 * 1024), 2)}MB"
        else:
            return f"{round(lengthBytes / (1024 * 1024 * 1024), 2)}GB"

    def printProgress(self, progress: int, filesize: int):
        speed = (self.lengthBytesDownloaded - self.lastLengthBytesDownloaded) * 2
        print(
            f"{round((float(progress) / filesize) * 100, 2)}% ({self._lengthBytesToString(speed)}/S): "
            f"{self._lengthBytesToString(progress)}/{self._lengthBytesToString(filesize)}")
        self.lastLengthBytesDownloaded = progress

    def _keepPrintProgress(self):
        bar = progressbar.ProgressBar(
            widgets=[
                '进度: ',
                progressbar.Percentage(),
                ' ',
                progressbar.Bar(),
                ' ',
                progressbar.FileTransferSpeed(),
                ' | ',
                progressbar.ETA()
            ],
            max_value=self.fileSize
        )
        bar.start()
        while True:
            if self.enablePrint:
                bar.update(self.lengthBytesDownloaded)
                # self.printProgress(self.lengthBytesDownloaded, self.fileSize)
            if self.lengthBytesDownloaded >= self.fileSize:
                break
            time.sleep(0.5)
        bar.finish()

    def download(self, url, fileName, loop=None):
        response = requests.head(url, headers=self.headers, allow_redirects=True)
        if 302 in [history.status_code for history in response.history]:
            url = response.url
            print(f"Redirect to {url}")
        fileSize = int(response.headers['Content-Length'])
        self.fileSize = fileSize
        numChunks, chunkSize, lastChunkSize = self.calculateChunkSize(fileSize)
        print(f"开始下载：{fileName}, "
              f"总大小：{self._lengthBytesToString(fileSize)}, "
              f"分片大小：{self._lengthBytesToString(chunkSize)} "
              f"分片数量：{numChunks}")
        if loop is None:
            loop = asyncio.get_event_loop()
        if self.enablePrint:
            thread = threading.Thread(target=self._keepPrintProgress)
            thread.start()
        loop.run_until_complete(self._startDownload(url, fileName, numChunks, chunkSize, lastChunkSize))
        if self.enablePrint:
            thread.join()

    async def download_async(self, url, fileName):
        response = requests.head(url)
        fileSize = int(response.headers['Content-Length'])
        self.fileSize = fileSize
        numChunks, chunkSize, lastChunkSize = self.calculateChunkSize(fileSize)
        print(f"开始下载：{fileName}, "
              f"总大小：{self._lengthBytesToString(fileSize)}, "
              f"分片大小：{self._lengthBytesToString(chunkSize)} "
              f"分片数量：{numChunks}")
        if self.enablePrint:
            thread = threading.Thread(target=self._keepPrintProgress)
            thread.start()
        await self._startDownload(url, fileName, numChunks, chunkSize, lastChunkSize)
        if self.enablePrint:
            thread.join()
