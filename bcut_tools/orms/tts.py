import json
from enum import Enum
from pydantic import BaseModel, field_validator
from typing import List


class VoiceRspSchema(BaseModel):
    """
    声音信息
    """

    id: int
    name: str
    cover: str
    extra: str
    pool_extra: str
    state: int
    material_type: int
    voice: str
    voice_engine: str


class CategorySchema(BaseModel):
    """
    类别信息
    """

    id: int
    title: str
    materials: List[VoiceRspSchema]

class ResultStateEnum(Enum):
    """任务状态枚举"""

    COMPLETE = 0  # 完成
    RUNING = 1  # 运行中

class TaskCreateRspSchema(BaseModel):
    """任务创建响应"""

    task_id: str
    poll_time: int
    result: str
    mark: int
    timeout_time: int
    state: int


class ResultMediaRspSchema(BaseModel):
    """媒体响应"""

    audio_url: str
    meta_url: str
    sep_url: str


class ResultRspSchema(BaseModel):
    """任务结果查询响应"""

    task_id: str
    result: ResultMediaRspSchema
    remark: str
    state: ResultStateEnum

    @field_validator("result", mode="before")
    def parse_result(cls, v):
        if isinstance(v, str):
            v = json.loads(v)
        return v
