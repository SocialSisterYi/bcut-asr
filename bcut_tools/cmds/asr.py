import logging
import sys
import time
import ffmpeg


from bcut_tools.errors import APIError
from bcut_tools.orms.asr import (
    ResultStateEnum,
)
from bcut_tools.utils import ffmpeg_render
from bcut_tools.asr import BcutASR

INFILE_FMT = ["flac", "aac", "m4a", "mp3", "wav"]
OUTFILE_FMT = ["srt", "json", "lrc", "txt"]


def asr_cmd(args) -> int:
    # 处理输入文件情况
    infile = args.input
    infile_name = infile.name
    if infile_name == "<stdin>":
        logging.error("输入文件错误")
        return -1
    suffix = infile_name.rsplit(".", 1)[-1]
    if suffix in INFILE_FMT:
        infile_fmt = suffix
        infile_data = infile.read()
    else:
        # ffmpeg分离视频伴音
        logging.info("非标准音频文件, 尝试调用ffmpeg转码")
        try:
            infile_data = ffmpeg_render(infile_name)
        except ffmpeg.Error:
            logging.error("ffmpeg转码失败")
            return -1
        else:
            logging.info("ffmpeg转码完成")
            infile_fmt = "aac"

    # 处理输出文件情况（保留原有判定与写出方式）
    outfile = args.output
    if outfile is None:
        # 未指定输出文件，默认为文件名同输入，可以 -t 传参，默认str格式
        if args.format is not None:
            outfile_fmt = args.format
        else:
            outfile_fmt = "srt"
    else:
        # 指定输出文件
        outfile_name = outfile.name
        if outfile.name == "<stdout>":
            # stdout情况，可以 -t 传参，默认str格式
            if args.format is not None:
                outfile_fmt = args.format
            else:
                outfile_fmt = "srt"
        else:
            suffix = outfile_name.rsplit(".", 1)[-1]
            if suffix in OUTFILE_FMT:
                outfile_fmt = suffix
            else:
                logging.error("输出格式错误")
                return -1

    interval = args.interval
    if interval is None:
        interval = 1.0
    # 开始执行转换逻辑
    asr = BcutASR()
    asr.set_data(raw_data=infile_data, data_fmt=infile_fmt)
    try:
        # 上传文件
        asr.upload()
        # 创建任务
        asr.create_task()
        while True:
            # 轮询检查任务状态
            task_resp = asr.result()
            match task_resp.state:
                case ResultStateEnum.STOP:
                    logging.info("等待识别开始")
                case ResultStateEnum.RUNING:
                    logging.info(f"识别中 {task_resp.remark}")
                case ResultStateEnum.ERROR:
                    logging.error(f"识别失败 {task_resp.remark}")
                    sys.exit(-1)
                case ResultStateEnum.COMPLETE:
                    logging.info("识别成功")
                    outfile_name = f"{infile_name.rsplit('.', 1)[-2]}.{outfile_fmt}"
                    outfile = open(outfile_name, "w", encoding="utf8")
                    # 识别成功, 回读字幕数据
                    result = task_resp.parse()
                    break
            time.sleep(interval)
        if not result.has_data():
            logging.error("未识别到语音")
            return -1
        match outfile_fmt:
            case "srt":
                outfile.write(result.to_srt())
            case "lrc":
                outfile.write(result.to_lrc())
            case "json":
                outfile.write(result.model_dump_json())
            case "txt":
                outfile.write(result.to_txt())
        outfile.close()
        logging.info(f"转换成功: {outfile_name}")
    except APIError as err:
        logging.error("接口错误: %s", err)
        return -1
    return 0
