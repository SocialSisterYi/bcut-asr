import logging
import time
from rich.console import Console
from rich.table import Table


from bcut_tools.errors import APIError
from bcut_tools.utils import download_file, download_json
from bcut_tools.orms.tts import ResultStateEnum
from bcut_tools.constants import HEADERS
from bcut_tools.tts import BcutTTS

API_BASE_URL = "https://member.bilibili.com/x/creative-tool"

# 创建任务
API_CREATE_TASK = API_BASE_URL + "/rubick-interface/task"

# 查询结果
API_QUERY_RESULT = API_BASE_URL + "/rubick-interface/task/result"

# 可用声音列表
API_VOICE_LIST = API_BASE_URL + "/bcut/pc/tts/list"


def tts_cmd(args) -> int:
    tts = BcutTTS()
    interval = args.interval
    if interval is None:
        interval = 1.0

    text = args.text
    if text is None:
        logging.error("缺少合成文本")
        return -1

    pitch_rate = args.pitch_rate
    sample_rate = args.sample_rate
    speech_rate = args.speech_rate
    volume = args.volume
    voice = args.voice
    voice_engine = args.voice_engine
    output = args.output
    if output is None:
        audio_output_name = f"tts_{voice}_{int(time.time())}.wav"
    else:
        audio_output_name = output.name
    meta_output = args.meta_output
    if meta_output is None:
        meta_output_name = f"tts_{voice}_{int(time.time())}_meta.json"
    else:
        meta_output_name = meta_output.name

    sep_output = args.sep_output
    if sep_output is None:
        sep_output_name = f"tts_{voice}_{int(time.time())}_sep.json"
    else:
        sep_output_name = sep_output.name

    tts.set_data(
        text=text,
        voice=voice,
        voice_engine=voice_engine,
        pitch_rate=pitch_rate,
        sample_rate=sample_rate,
        speech_rate=speech_rate,
        volume=volume,
    )

    try:
        # 创建任务
        tts.create_task()
        logging.info("任务创建成功, 任务ID: %s", tts.task_id)
        while True:
            # 轮询检查任务状态
            task_resp = tts.query_result()
            match task_resp.state:
                case ResultStateEnum.RUNING:
                    logging.info(f"合成中 {task_resp.remark}")
                case ResultStateEnum.COMPLETE:
                    logging.info("合成成功")
                    audio_data = task_resp.result
                    break
                case _:
                    logging.warning("未知状态 %s", task_resp.state)
            time.sleep(interval)
        if not audio_data:
            logging.error("未获取到音频数据")
            return -1

        # 下载 audio 和 meta.json
        audio_url = audio_data.audio_url
        meta_url = audio_data.meta_url
        sep_url = audio_data.sep_url

        download_file(audio_url, audio_output_name, HEADERS)
        download_json(meta_url, meta_output_name, HEADERS)
        download_json(sep_url, sep_output_name, HEADERS)

        logging.info(f"音频文件: {audio_output_name}")
        logging.info(f"元数据文件: {meta_output_name}")
        logging.info(f"分割数据文件: {sep_output_name}")
    except APIError as err:
        logging.error("接口错误: %s", err)
        return -1
    return 0


def available_voices_cmd(args) -> int:
    """使用 rich 输出可用的声音列表"""
    try:
        tts = BcutTTS()
        categories = tts.get_avail_voices()

        # 创建表格
        table = Table(
            title="必剪可用语音列表",
            box=None,
            show_header=True,
            header_style="bold cyan",
            padding=(0, 1),
            collapse_padding=True,
        )

        table.add_column("Category", width=20, no_wrap=True)
        table.add_column("Name", width=20, no_wrap=True)
        table.add_column("Voice", width=30, overflow="fold")
        table.add_column("Voice Engine", width=15)

        console = Console()

        for category in categories:
            category_name = category.title or "未分类"
            for i, voice in enumerate(category.materials):
                voice_id = voice.voice
                engine = voice.voice_engine or "unknown"

                if i == 0:
                    table.add_row(category_name, voice.name, voice_id, engine)
                else:
                    # 后续行分类留空
                    table.add_row("", voice.name, voice_id, engine)

        console.print(table)
        return 0

    except Exception as e:
        logging.error("显示声音列表失败: %s", e)
        return -1