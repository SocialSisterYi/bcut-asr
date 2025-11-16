import json
import requests
from typing import Optional


from bcut_tools.errors import APIError
from bcut_tools.orms.tts import TaskCreateRspSchema, ResultRspSchema, CategorySchema
from bcut_tools.utils import download_file, download_json
from bcut_tools.orms.tts import ResultStateEnum
from bcut_tools.constants import HEADERS

API_BASE_URL = "https://member.bilibili.com/x/creative-tool"

# 创建任务
API_CREATE_TASK = API_BASE_URL + "/rubick-interface/task"

# 查询结果
API_QUERY_RESULT = API_BASE_URL + "/rubick-interface/task/result"

# 可用声音列表
API_VOICE_LIST = API_BASE_URL + "/bcut/pc/tts/list"

class BcutTTS:
    "必剪 TTS 接口"

    session: requests.Session
    text: str
    pitch_rate: int
    sample_rate: int
    speech_rate: int
    voice: str
    voice_engine: str
    volume: int
    __model_id = "tts_common_bcut_pc"
    task_id: Optional[str]

    def __init__(
        self,
    ):
        self.session = requests.Session()

    def set_data(
        self,
        text: str,
        pitch_rate: int = 0,
        sample_rate: int = 24000,
        speech_rate: int = 0,
        voice: str = "dingzhen",
        voice_engine: str = "bili-fewshot",
        volume: int = 50,
    ):
        self.text = text
        self.pitch_rate = pitch_rate
        self.sample_rate = sample_rate
        self.speech_rate = speech_rate
        self.voice = voice
        self.voice_engine = voice_engine
        self.volume = volume

    def get_avail_voices(self) -> list[CategorySchema]:
        resp = self.session.get(
            API_VOICE_LIST,
            headers=HEADERS,
        )
        if resp.status_code == 200:
            resp_data = resp.json()
            if resp_data.get("code") == 0:
                return [CategorySchema.model_validate(category) for category in resp_data["data"]["categories"]]
        raise APIError(code=resp.status_code, msg=resp.text)

    def create_task(self):
        resp = self.session.post(
            API_CREATE_TASK,
            json={
                "model_id": self.__model_id,
                "params": json.dumps(
                    {
                        "expect_mark": 0,
                        "raw_data": self.text,
                        "raw_params": {
                            "pitch_rate": self.pitch_rate,
                            "sample_rate": self.sample_rate,
                            "speech_rate": self.speech_rate,
                            "voice": self.voice,
                            "voice_engine": self.voice_engine,
                            "volume": self.volume,
                        },
                    },
                    ensure_ascii=False,
                ),
            },
            headers=HEADERS,
        )
        if resp.status_code == 200:
            resp_data = resp.json()
            if resp_data.get("code") == 0:
                self.task_id = resp_data["data"]["task_id"]
                return TaskCreateRspSchema.model_validate(resp_data["data"])
        raise APIError(code=resp.status_code, msg=resp.text)

    def query_result(self, task_id: Optional[str] = None) -> ResultRspSchema:
        resp = self.session.get(
            API_QUERY_RESULT,
            params={
                "model_id": self.__model_id,
                "task_id": task_id or self.task_id,
            },
            headers=HEADERS,
        )
        if resp.status_code == 200:
            resp_data = resp.json()
            if resp_data.get("code") == 0:
                return ResultRspSchema.model_validate(resp_data["data"])
        raise APIError(code=resp.status_code, msg=resp.text)
