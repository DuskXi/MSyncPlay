import math
import time

import numpy as np
import pyaudio
from loguru import logger
from numba import jit

from audio import PlayLayer
from pydub import AudioSegment
import sys
import requests
import asyncio
import JModel
import datamodel

from paralleldownload import ParallelDownload

sys.path.append(r"C:\Program Files\ffmpeg\bin")


def get_arr(path):
    sound = AudioSegment.from_file(path)
    array = np.array(sound.get_array_of_samples())
    if sound.channels == 2:
        array = array.reshape((-1, 2))
    else:
        array = array.reshape((-1, 1))
    return sound.frame_rate, sound.frame_count(), array


def play(path):
    rate, number_frames, data = get_arr(path)
    audio_frame = 0
    audio_frame_step = (1 / rate)
    p = pyaudio.PyAudio()  # 创建音频播放器
    stream = p.open(format=pyaudio.paInt16, channels=2, rate=rate, output=True)
    while audio_frame < number_frames:
        stream.write(
            data[audio_frame].tostring())
        audio_frame += 1
        if audio_frame % rate == 0:
            logger.debug(f"\nstream.get_time(): {stream.get_time()}"
                         f"\nstream.get_output_latency(): {stream.get_output_latency()}"
                         f"\nstream.get_input_latency(): {stream.get_input_latency()}"
                         f"\nstream.get_read_available(): {stream.get_read_available()}")


def test():
    print()
    # play(r"D:\projects\playTogather\client\cache/bcpgQOuKuMY.m4a")
    # parallelDownload = ParallelDownload(maxThread=1000)
    # parallelDownload.download("https://lon-gb-ping.vultr.com/vultr.com.1000MB.bin", "vultr.com.1000MB.bin")
    # play(r"D:\projects\playTogather\client\cache\JhewXi1UeqQ.m4a")
    # playLayer = PlayLayer(
    #     "https://r2---sn-5n3-n1ql.googlevideo.com/videoplayback?expire=1637103510&ei=NuOTYZHiJfqoxN8P-5-QwAQ&ip=31.205.236.29&id=o-AIrJzfVFpLchikfEvkPSYHwwOpvDmx5oQKvLbUjvxMyb&itag=140&source=youtube&requiressl=yes&mh=kw&mm=31%2C29&mn=sn-5n3-n1ql%2Csn-aigzrnld&ms=au%2Crdu&mv=m&mvi=2&pcm2cms=yes&pl=19&initcwndbps=2156250&vprv=1&mime=audio%2Fmp4&gir=yes&clen=3896046&dur=240.674&lmt=1613798414511546&mt=1637081588&fvip=3&keepalive=yes&fexp=24001373%2C24007246&c=ANDROID&txp=6311222&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cvprv%2Cmime%2Cgir%2Cclen%2Cdur%2Clmt&sig=AOq0QJ8wRQIgXwwCxGSugwdxfrC661NYCz_8X3_EqO0sV4jlzVozDkcCIQDjTG3LhlWbkD7zofv4mDOrGwqVCwn5k1E1Ez5JRugDgA%3D%3D&lsparams=mh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpcm2cms%2Cpl%2Cinitcwndbps&lsig=AG3C_xAwRAIgW2218DT_KDsHs8W8M7HjJ5Mr3D8LF3yLnCofjnQOelYCICxeF0UIgqh5ik7MbrEyIpWfHl50_9v-G7tB3O6c_u5j")
    # playLayer = PlayLayer(r"D:\projects\playTogather\client\cache/JhewXi1UeqQ.m4a")
    # playLayer.benchmark_time = time.time()
    # playLayer.isRun = True
    # playLayer.play()
    # playLayer.set_position(20)
    # time.sleep(10)
    # playLayer.stop()
    # time.sleep(1000)
    # result = JModel.to_object({"testNumber": 0, "testClass": {"name": 123}}, JModel.TestObject)
    result = datamodel.DataModel(json='{"playStatus":"play"}')
    print(result)
    changed = result.update('{"playStatus":"pause", "benchmarkDevice":"win", "benchmarkTimestamp": 123}')
    print(result)


if __name__ == '__main__':
    test()
