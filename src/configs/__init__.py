# -*- coding: utf-8 -*-
from src.configs.log_config import logger
from src.configs.settings import DevSetting, ProdSetting, UnitTestSetting


def get_setting():
    import os

    run_mode = os.getenv("RUNTIME_ENV", "dev")
    match run_mode:
        case 'unit_test':
            return UnitTestSetting()
        case 'dev':
            return DevSetting()
        case 'prod':
            return ProdSetting()
        case _:
            return DevSetting()
