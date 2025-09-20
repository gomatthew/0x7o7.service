# -*- coding: utf-8 -*-
from enum import Enum,StrEnum


class ModelTypeEnum(StrEnum):
    LLM = 'llm'
    EMBEDDING = 'embedding'

class MessageTypeEnum(StrEnum):
    TEXT = 'text'
    IMAGE = 'image'
    AUDIO = 'audio'
    VIDEO = 'video'

if __name__ == '__main__':
    a=ModelTypeEnum.LLM
    print(a)