# -*- coding: utf-8 -*-
from fastapi import APIRouter
from src.server.service import upload_file, download_file,get_goods_list

service_router = APIRouter(prefix="/service", tags=['服务类api'])
service_router.post('/upload_file', summary='上传文件')(upload_file)
service_router.get('/download_file', summary='下载文件')(download_file)
service_router.get('/get_good',summary="获得产品列表")(get_goods_list)
