# -*- coding: utf-8 -*-
import os
import sys
import uvicorn
import platform
from src.server import create_app, create_tables
from src.configs import get_setting, logger

logger.info('[START SERVER]')
logger.info(f'Runtime Mode | {os.getenv("RUNTIME_ENV")}')
logger.info(f'Operate System | {platform.platform()}')
logger.info(f'Python Edition | {sys.version}')
app = create_app()

if __name__ == '__main__':
    create_tables()
    settings = get_setting()
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
