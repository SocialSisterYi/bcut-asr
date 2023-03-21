import logging
import time
from os import PathLike
from pathlib import Path
from typing import Literal, Optional
import requests
import sys
import ffmpeg
from .orm import (ResourceCompleteRspSchema, ResourceCreateRspSchema,
                  ResultRspSchema, ResultStateEnum, TaskCreateRspSchema)

__version__ = '0.0.2'

API_REQ_UPLOAD    = 'https://member.bilibili.com/x/bcut/rubick-interface/resource/create' # 申请上传
API_COMMIT_UPLOAD = 'https://member.bilibili.com/x/bcut/rubick-interface/resource/create/complete' # 提交上传
API_CREATE_TASK   = 'https://member.bilibili.com/x/bcut/rubick-interface/task' # 创建任务
API_QUERY_RESULT  = 'https://member.bilibili.com/x/bcut/rubick-interface/task/result' # 查询结果

SUPPORT_SOUND_FORMAT = Literal['flac', 'aac', 'm4a', 'mp3', 'wav']

INFILE_FMT = ('flac', 'aac', 'm4a', 'mp3', 'wav')
OUTFILE_FMT = ('srt', 'json', 'lrc', 'txt')


def ffmpeg_render(media_file: str) -> bytes:
    '提取视频伴音并转码为aac格式'
    out, err = (ffmpeg
                .input(media_file, v='warning')
                .output('pipe:', ac=1, format='adts')
                .run(capture_stdout=True)
                )
    return out


def run_everywhere(argg):
    logging.basicConfig(format='%(asctime)s - [%(levelname)s] %(message)s', level=logging.INFO)
    # 处理输入文件情况
    infile = argg.input
    infile_name = infile.name
    if infile_name == '<stdin>':
        logging.error('输入文件错误')
        sys.exit(-1)
    suffix = infile_name.rsplit('.', 1)[-1]
    if suffix in INFILE_FMT:
        infile_fmt = suffix
        infile_data = infile.read()
    else:
        # ffmpeg分离视频伴音
        logging.info('非标准音频文件, 尝试调用ffmpeg转码')
        try:
            infile_data = ffmpeg_render(infile_name)
        except ffmpeg.Error:
            logging.error('ffmpeg转码失败')
            sys.exit(-1)
        else:
            logging.info('ffmpeg转码完成')
            infile_fmt = 'aac'

    # 处理输出文件情况
    outfile = argg.output
    if outfile is None:
        # 未指定输出文件，默认为文件名同输入，可以 -t 传参，默认str格式
        if argg.format is not None:
            outfile_fmt = argg.format
        else:
            outfile_fmt = 'srt'
    else:
        # 指定输出文件
        outfile_name = outfile.name
        if outfile.name == '<stdout>':
            # stdout情况，可以 -t 传参，默认str格式
            if argg.format is not None:
                outfile_fmt = argg.format
            else:
                outfile_fmt = 'srt'
        else:
            suffix = outfile_name.rsplit('.', 1)[-1]
            if suffix in OUTFILE_FMT:
                outfile_fmt = suffix
            else:
                logging.error('输出格式错误')
                sys.exit(-1)

    # 开始执行转换逻辑
    asr = BcutASR()
    asr.set_data(raw_data=infile_data, data_fmt=infile_fmt)
    try:
        # 上传文件
        asr.upload()
        # 创建任务
        task_id = asr.create_task()
        while True:
            # 轮询检查任务状态
            task_resp = asr.result()
            match task_resp.state:
                case ResultStateEnum.STOP:
                    logging.info(f'等待识别开始')
                case ResultStateEnum.RUNING:
                    logging.info(f'识别中-{task_resp.remark}')
                case ResultStateEnum.ERROR:
                    logging.error(f'识别失败-{task_resp.remark}')
                    sys.exit(-1)
                case ResultStateEnum.COMPLETE:
                    outfile_name = f"{infile_name.rsplit('.', 1)[-2]}.{outfile_fmt}"
                    outfile = open(outfile_name, 'w', encoding='utf8')
                    logging.info(f'识别成功')
                    # 识别成功, 回读字幕数据
                    result = task_resp.parse()
                    break
            time.sleep(300.0)
        if not result.has_data():
            logging.error('未识别到语音')
            sys.exit(-1)
        match outfile_fmt:
            case 'srt':
                outfile.write(result.to_srt())
            case 'lrc':
                outfile.write(result.to_lrc())
            case 'json':
                outfile.write(result.json())
            case 'txt':
                outfile.write(result.to_txt())
        logging.info(f'转换成功: {outfile_name}')
    except APIError as err:
        logging.error(f'接口错误: {err.__str__()}')
        sys.exit(-1)

class APIError(Exception):
    '接口调用错误'
    def __init__(self, code, msg) -> None:
        self.code = code
        self.msg = msg
        super().__init__()
    def __str__(self) -> str:
        return f'{self.code}:{self.msg}'

class BcutASR:
    '必剪 语音识别接口'
    session: requests.Session
    sound_name: str
    sound_bin: bytes
    sound_fmt: SUPPORT_SOUND_FORMAT
    __in_boss_key: str
    __resource_id: str
    __upload_id: str
    __upload_urls: list[str]
    __per_size: int
    __clips: int
    __etags: list[str]
    __download_url: str
    task_id: str
    
    def __init__(self, file: Optional[str | PathLike] = None) -> None:
        self.session = requests.Session()
        self.task_id = None
        self.__etags = []
        if file:
            self.set_data(file)
    
    def set_data(self,
        file: Optional[str | PathLike] = None, 
        raw_data: Optional[bytes] = None,
        data_fmt: Optional[SUPPORT_SOUND_FORMAT] = None
    ) -> None:
        '设置欲识别的数据'
        if file:
            if not isinstance(file, (str, PathLike)):
                raise TypeError('unknow file ptr')
            # 文件类
            file = Path(file)
            self.sound_bin = open(file, 'rb').read()
            suffix = data_fmt or file.suffix[1:]
            self.sound_name = file.name
        elif raw_data:
            # bytes类
            self.sound_bin = raw_data
            suffix = data_fmt
            self.sound_name = f'{int(time.time())}.{suffix}'
        else:
            raise ValueError('none set data')
        if suffix not in SUPPORT_SOUND_FORMAT.__args__:
            raise TypeError('format is not support')
        self.sound_fmt = suffix
        logging.info(f'加载文件成功: {self.sound_name}')
    
    def upload(self) -> None:
        '申请上传'
        if not self.sound_bin or not self.sound_fmt:
            raise ValueError('none set data')
        resp = self.session.post(API_REQ_UPLOAD, data={
            'type': 2,
            'name': self.sound_name,
            'size': len(self.sound_bin),
            'resource_file_type': self.sound_fmt,
            'model_id': 7
        })
        resp.raise_for_status()
        resp = resp.json()
        code = resp['code']
        if code:
            raise APIError(code, resp['message'])
        resp_data = ResourceCreateRspSchema.parse_obj(resp['data'])
        self.__in_boss_key = resp_data.in_boss_key
        self.__resource_id = resp_data.resource_id
        self.__upload_id = resp_data.upload_id
        self.__upload_urls = resp_data.upload_urls
        self.__per_size = resp_data.per_size
        self.__clips = len(resp_data.upload_urls)
        logging.info(f'申请上传成功, 总计大小{resp_data.size // 1024}KB, {self.__clips}分片, 分片大小{resp_data.per_size // 1024}KB: {self.__in_boss_key}')
        self.__upload_part()
        self.__commit_upload()
        
    def __upload_part(self) -> None:
        '上传音频数据'
        for clip in range(self.__clips):
            start_range = clip * self.__per_size
            end_range = (clip + 1) * self.__per_size
            logging.info(f'开始上传分片{clip}: {start_range}-{end_range}')
            resp = self.session.put(self.__upload_urls[clip],
                data=self.sound_bin[start_range:end_range],
            )
            resp.raise_for_status()
            etag = resp.headers.get('Etag')
            self.__etags.append(etag)
            logging.info(f'分片{clip}上传成功: {etag}')
    
    def __commit_upload(self) -> None:
        '提交上传数据'
        resp = self.session.post(API_COMMIT_UPLOAD, data={
            'in_boss_key': self.__in_boss_key,
            'resource_id': self.__resource_id,
            'etags': ','.join(self.__etags),
            'upload_id': self.__upload_id,
            'model_id': 7
        })
        resp.raise_for_status()
        resp = resp.json()
        code = resp['code']
        if code:
            raise APIError(code, resp['message'])
        resp_data = ResourceCompleteRspSchema.parse_obj(resp['data'])
        self.__download_url = resp_data.download_url
        logging.info(f'提交成功')
    
    def create_task(self) -> str:
        '开始创建转换任务'
        resp = self.session.post(API_CREATE_TASK, json={
            'resource': self.__download_url,
            'model_id': '7'
        })
        resp.raise_for_status()
        resp = resp.json()
        code = resp['code']
        if code:
            raise APIError(code, resp['message'])
        resp_data = TaskCreateRspSchema.parse_obj(resp['data'])
        self.task_id = resp_data.task_id
        logging.info(f'任务已创建: {self.task_id}')
        return self.task_id
    
    def result(self, task_id: Optional[str] = None) -> ResultRspSchema:
        '查询转换结果'
        resp = self.session.get(API_QUERY_RESULT, params={
            'model_id': 7,
            'task_id': task_id or self.task_id
        })
        resp.raise_for_status()
        resp = resp.json()
        code = resp['code']
        if code:
            raise APIError(code, resp['message'])
        return ResultRspSchema.parse_obj(resp['data'])
