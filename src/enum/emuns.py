# -*- coding: utf-8 -*-
from enum import Enum,StrEnum


class ModelTypeEnum(StrEnum):
    LLM = 'llm'
    EMBEDDING = 'embedding'



if __name__ == '__main__':
    a=ModelTypeEnum.LLM
    print(a)