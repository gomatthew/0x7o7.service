# -*- coding: utf-8 -*-
from fastapi import Query
from src.server.dto import ApiCommonResponseDTO
from src.configs import get_setting, logger


def get_goods_list(user_id: str = Query(..., description='')):
    logger.info(f'🟢 获得产品List[START]:{user_id}')
    data = [{'good_id': 'c5078aefb7914d4e8330cf76535357fd', 'good_name': '苹果'},
            {'good_id': '9e0a546dc2b943adaae8dcfc245ca85c', 'good_name': '香蕉'},
            {'good_id': '47fc4a922c8649568ed68afac5e62bf7', 'good_name': '鸭梨🍐'}]
    logger.info(f'🟢 获得产品List[END]')
    return ApiCommonResponseDTO(data=data).model_dict()
