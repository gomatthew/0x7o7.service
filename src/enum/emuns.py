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

class FileTypeEnum(StrEnum):
    KB_FILE = 'kb_file'
    KB_FILE_SEGMENT = 'kb_file_segment'

if __name__ == '__main__':
    a=ModelTypeEnum.LLM
    print(a)