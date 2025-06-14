# -*- coding: utf-8 -*-
import os
from src.configs.settings import BaseSetting

timeout = 0
daemon = True  # 设置守护进程
bind = f'{BaseSetting.APP_HOST}:{BaseSetting.APP_PORT}'  # 监听内网端口8000
chdir = './'  # 工作目录
worker_class = 'uvicorn.workers.UvicornWorker'  # 工作模式
# workers = multiprocessing.cpu_count() + 1  # 并行工作进程数 核心数*2+1个
workers = BaseSetting.GUNICORN_WORKER_NUMBER
threads = BaseSetting.GUNICORN_THREAD_NUMBER  # 指定每个工作者的线程数
worker_connections = 2000  # 设置最大并发量
loglevel = 'INFO'  # 错误日志的日志级别
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'
# 设置访问日志和错误信息日志路径
log_dir = BaseSetting.LOG_PATH
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

pidfile = os.path.join(log_dir, 'gunicorn.pid')
accesslog = os.path.join(log_dir, "app.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")

# gunicorn -c deploy/gunicorn_conf.py main:app
