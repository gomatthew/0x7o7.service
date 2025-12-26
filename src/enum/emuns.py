# -*- coding: utf-8 -*-
from enum import StrEnum


class RecordStatusEnum(StrEnum):
    ACTIVATE = '1'
    INACTIVATE = '0'


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


class UploadRagFileTypeEnum(StrEnum):
    EMBEDDING = 'embedding'
    FAIL = 'fail'
    COMPLETED = 'completed'


if __name__ == '__main__':
    a = ModelTypeEnum.LLM
    print(a)
