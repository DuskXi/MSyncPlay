# MSyncPlay [![wakatime](https://wakatime.com/badge/github/DuskXi/MSyncPlay.svg)](https://wakatime.com/badge/github/DuskXi/MSyncPlay)

一个多设备同步播放软件

总体上已经可以使用(有bug，欢迎发issue)

完美同时播放，无论延迟多高

暂时只支持YouTube视频链接（自动解析为音频，歌单添加歌曲时只需要输入视频链接，每次播放会自动解析）

使用方法:

在所有设备都可以访问的一台计算机上运行server/main.py

对于server端:

```pip
Flask==1.1.2
Flask_SocketIO==5.1.1
loguru==0.5.1
pytube==11.0.2
```

然后在所有负责播放的设备上运行client/main.py

client的服务器配置在config.json中

对于client端:

```pip
pydub==0.25.1
loguru==0.5.1
numpy==1.19.0
wget==3.2
PyAudio==0.2.11
requests==2.25.1
numba==0.54.1
gevent_socketio==0.3.6
progressbar33==2.4
```

在安装PyAudio之前可能需要安装PortAudio

## English:

A multi-device synchronized playback software

Overall already works(There is a few bugs, welcome to send issues)

Perfect simultaneous playback, no matter how high the delay is

Only YouTube video links are supported for now (automatically parsed to audio, just enter the video link when adding songs to the song list, and it will be parsed automatically every time you play)

How to use:

Run server/main.py on a computer accessible by all devices

For server side:

```pip
Flask==1.1.2
Flask_SocketIO==5.1.1
loguru==0.5.1
pytube==11.0.2
```

Then run client/main.py on all the devices responsible for playback

The client's server configuration is in config.json

For the client side:

```pip
pydub==0.25.1
loguru==0.5.1
numpy==1.19.0
wget==3.2
PyAudio==0.2.11
requests==2.25.1
numba==0.54.1
gevent_socketio==0.3.6
progressbar33==2.4
```

You may need to install PortAudio before installing PyAudio
