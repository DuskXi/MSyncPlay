import json
import sys
import threading
import time

import numpy as np
import socketio

# standard Python
from loguru import logger

from audio import Audio
from core import Core

sio = socketio.Client()
audio = None
time_send = 0
isRun = True
differences = []
difference = 0
name = "1"


@sio.on('play')
def play(data):
    global audio
    global difference
    jObject = json.loads(data)
    startTime = jObject["time"]
    while True:
        time.sleep(0.0001)
        if time.time() >= startTime - difference:
            break
    audio.play()


@sio.on('load')
def load(data):
    global audio
    jObject = json.loads(data)
    audio = Audio(jObject["url"])
    logger.info("加载完毕...")


@sio.on('pause')
def pause():
    global audio
    audio.pause()


@sio.on('exit')
def end():
    global isRun
    isRun = False


@sio.on('time')
def correctTime(data):
    time_now = time.time()
    global time_send
    global difference
    global differences
    global name
    jObject = json.loads(data)
    if jObject["name"] != name:
        return
    if jObject['times'] > 5:
        difference = np.average(differences)
        logger.info(f"平均时间差: {round(difference * 1000)}ms")
        return
    time_receive = jObject["time_receive"]
    time_reply = jObject["time_reply"]
    time_difference = (time_receive - time_send) - ((time_now - time_send) / 2)
    differences.append(time_difference)
    delay = time_now - time_send
    deviation = ((time_reply - time_difference) + delay) - time_now
    logger.info(
        f"第{jObject['times']}次矫正: 时间差为 {round(time_difference * 1000, 2)} ms, 误差为: {round(deviation * 1000, )} ms, 延迟为: {round(delay * 1000, 2)} ms")
    logger.info(
        f"    time_send: {time_send}, time_now: {time_now}, time_receive: {time_receive}, time_reply: {time_reply}")
    time_send = time.time()
    sio.emit("time", '{"times":' + str(jObject['times'] + 1) + ', "name":"' + name + '"}')


def read_file(filename, encoding='utf-8'):
    with open(filename, encoding=encoding) as f:
        return f.read()


def run():
    config = read_file("config.json") if "-f" not in sys.argv else read_file(sys.argv[sys.argv.index("-f") + 1])
    config = json.loads(config)
    core = Core(config["redress_intervals"])
    core.bind()
    core.connect(config["server"])
    core.run()


def main():
    global time_send
    global differences
    global isRun
    sio.connect('http://192.248.168.119:5000')
    sio.emit("register", "")
    while isRun:
        differences = []
        time_send = time.time()
        sio.emit("time", f'{{"times":1, "name":"{name}"}}')
        time.sleep(10)


if __name__ == "__main__":
    print()
    run()
    # main()
