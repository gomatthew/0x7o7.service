# -*- coding: utf-8 -*-
import io
from typing import Optional
from minio import Minio
from fastapi import Body, UploadFile, File
from src.configs import get_setting, logger
from src.server.db.repository import add_file_to_db
from src.server.dto import AddFileToDBDTO, ApiCommonResponseDTO

setting = get_setting()


class MinioInstance:
    def __init__(self, bucket_name):
        self.secret_key = setting.MINIO_SECRET_KEY
        self.access_key = setting.MINIO_ACCESS_KEY
        self.bucket = bucket_name
        self.service_url = setting.MINIO_SERVICE_URL
        self.minio_client = Minio(setting.MINIO_SERVICE_URL, setting.MINIO_ACCESS_KEY, setting.MINIO_SECRET_KEY,
                                  secure=False)

    def upload_minio(self, file_name, file_content):
        self.minio_client.put_object(setting.MINIO_BUCKET, file_name, io.BytesIO(file_content), len(file_content))
        return

    def download_minio(self, file_name):
        content = self.minio_client.get_object(bucket_name=setting.MINIO_BUCKET, object_name=file_name)
        return content.data


def upload_file(bucket_name: Optional[str] = Body(setting.MINIO_BUCKET),
                file: UploadFile = File(None, description="上传文件")):
    logger.info('🟢 文件上传[START]')
    minio_instance = MinioInstance(bucket_name)
    minio_instance.upload_minio(file.filename, file.file.read())
    new_file = AddFileToDBDTO()
    new_file.file_name = file.filename
    new_file.file_path = 'Minio'
    new_file.created_user_name = '0x7o7'
    new_file.created_user_id = '1'
    add_file_to_db(new_file)
    logger.info('🟢 文件上传[FINISH]')
    return ApiCommonResponseDTO(message="success").model_dict()


def download_file(bucket_name: Optional[str] = Body(setting.MINIO_BUCKET),
                  file_id: str = Body(..., description="文件id")):
    logger.info('🟢 文件下载[START]')
    minio_instance = MinioInstance(bucket_name)
    content = minio_instance.download_minio(file_id)
    logger.info('🟢 文件下载[END]')
    return ApiCommonResponseDTO(message='success', data=content).model_dict()
