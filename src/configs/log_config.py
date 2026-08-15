# -*- coding: utf-8 -*-
import os
import loguru
from src.configs.settings import BaseSetting


def get_logger():
    log_path = BaseSetting.LOG_PATH
    if not os.path.exists(log_path):
        os.makedirs(log_path, exist_ok=True)
    __logger = loguru.logger
    __logger.add(os.path.join(log_path, 'app.log'), rotation=BaseSetting.LOG_FILE_SIZE)
    return __logger


logger = get_logger()
