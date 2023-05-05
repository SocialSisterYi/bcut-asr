<h1 align="center">Bcut-ASR</h1>

使用必剪 API 进行云端语音字幕识别，支持 CLI 和 module 调用

## Feature

- 可直接上传`flac`, `aac`, `m4a`, `mp3`, `wav`音频格式
- 自动调用ffmpeg, 实现视频伴音和其他音频格式转码
- 支持`srt`, `json`, `lrc`, `txt`格式字幕输出
- 字幕支持断句和首位时间标记
- 可使用 stdout 输出字幕文本

## Install

```bash
git clone https://github.com/SocialSisterYi/bcut-asr
cd bcut-asr
```
Linux
```bash
./setup.py install
```
Windows
```cmd
python setup.py install
```

媒体转码需要安装 ffmpeg, 且系统 PATH 中可访问

## Usage

### CLI Interface

```bash
bcut_asr video.mp4
```

或

```bash
bcut_asr video.mp4 subttle.srt
```

或

```bash
bcut_asr video.mp4 -f srt - > subttle.srt
```

```
bcut_asr -h                
usage: bcut_asr [-h] [-f [{srt,json,lrc,txt}]] input [output]

必剪语音识别

positional arguments:
  input                 输入媒体文件
  output                输出字幕文件, 可stdout

options:
  -h, --help            show this help message and exit
  -f [{srt,json,lrc,txt}], --format [{srt,json,lrc,txt}]
                        输出字幕格式

支持输入音频格式: flac, aac, m4a, mp3, wav 支持自动调用ffmpeg提取视频伴音
```

### Module

```python
from bcut_asr import BcutASR
from bcut_asr.orm import ResultStateEnum

asr = BcutASR('voice.mp3')
asr.upload() # 上传文件
asr.create_task() # 创建任务

# 轮询检查结果
while True:
    result = asr.result()
    # 判断识别成功
    if result.state == ResultStateEnum.COMPLETE:
        break

# 解析字幕内容
subtitle = result.parse()
# 判断是否存在字幕
if subtitle.has_data():
    # 输出srt格式
    print(subtitle.to_srt())
```
