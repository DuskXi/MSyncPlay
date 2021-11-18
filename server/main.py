import json
import time

from flask import Flask, render_template
from flask_socketio import SocketIO
from loguru import logger
from server import Server

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

namespace = "app"


@socketio.on('JMessage')
def onJMessage(data):
    if type(data) == str:
        data = json.loads(eval(data))
    if data["type"] == "command":
        if data["command"] == "play":
            socketio.emit('play', json.dumps({"time": time.time() + 1}), broadcast=True)
        elif data["command"] == "load":
            music = {"url": data["url"]}
            socketio.emit('load', json.dumps(music), broadcast=True)
        elif data["command"] == "pause":
            socketio.emit('pause', broadcast=True)


@socketio.on('time')
def correctTime(data):
    time_receive = time.time()
    data = json.loads(data)
    socketio.emit('time',
                  f'{{"time_receive": {time_receive}, "time_reply": {time.time()}, "times": {data["times"]}, "name": "{data["name"]}"}}',
                  broadcast=False)


@socketio.on('connect')
def onConnect():
    pass
    # data = {
    #     "url": "https://r1---sn-5n3-n1qe.googlevideo.com/videoplayback?expire=1636762981&ei=BbGOYdhO5PXGAoneg9AL&ip=31.205.236.29&id=o-AFA_uXv5jDEgFfa7H9wP4pvA7vRYkqwMnz3Dwhl2mHpB&itag=251&source=youtube&requiressl=yes&mh=vt&mm=31%2C29&mn=sn-5n3-n1qe%2Csn-aigzrn76&ms=au%2Crdu&mv=m&mvi=1&pcm2cms=yes&pl=19&initcwndbps=1851250&vprv=1&mime=audio%2Fwebm&gir=yes&clen=3977997&dur=238.581&lmt=1624438242541492&mt=1636740775&fvip=1&keepalive=yes&fexp=24001373%2C24007246&c=ANDROID&txp=5431232&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cvprv%2Cmime%2Cgir%2Cclen%2Cdur%2Clmt&sig=AOq0QJ8wRQIgMtEqaVPlA_dpbx4Ogey43gU35yf-W2SPTep_orILvkcCIQCF7ET10uy-_iAPSFsQgXl-4UqIYB_yxieqYv3DZwRCrQ%3D%3D&lsparams=mh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpcm2cms%2Cpl%2Cinitcwndbps&lsig=AG3C_xAwRAIgLP0-0WXYI8lUCSNYtLLtq3C23piZkFgT23aaPjxxGNsCIA4bQXys86KTno3obf4cXYD8g_HJaXKOrU8Q5jck8bK8"}
    # socketio.emit('start', json.dumps(data))


@socketio.on('register')
def register(msg):
    logger.info(f'One computer Registering... {msg}')


@socketio.on('disconnect')
def onDisconnect():
    logger.info('Client offline...')


@app.route('/index')
def index():
    return render_template('index.html')


if __name__ == "__main__":
    server = Server("0.0.0.0", 5000)
    server.bind()
    server.load_music("PlayDataset.json")
    server.run()
    # socketio.run(app, host='0.0.0.0', port=5000)
