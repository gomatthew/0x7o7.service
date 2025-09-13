# -*- coding: utf-8 -*-
import io
import uuid
from typing import Optional
from urllib.parse import quote
from minio import Minio
from fastapi import Body, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from src.configs import get_setting, logger
from src.server.db.repository import add_file_to_db, get_file_by_id
from src.server.dto import AddFileToDBDTO, ApiCommonResponseDTO

setting = get_setting()


class MinioInstance:
    def __init__(self, bucket_name='service'):
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
        return content


def upload_file(bucket_name: Optional[str] = Body(setting.MINIO_BUCKET),
                file: UploadFile = File(None, description="上传文件")):
    logger.info('🟢 文件上传[START]')
    file_id = uuid.uuid4().hex
    minio_instance = MinioInstance(bucket_name)
    minio_instance.upload_minio(file_id, file.file.read())
    new_file = AddFileToDBDTO()
    new_file.file_id = file_id
    new_file.file_name = file.filename
    new_file.file_path = 'Minio'
    new_file.created_user_name = '0x7o7'
    new_file.created_user_id = '1'
    add_file_to_db(new_file)
    logger.info('🟢 文件上传[FINISH]')
    return ApiCommonResponseDTO(message="success", data={'file_id': file_id}).model_dict()


def download_file(bucket_name: Optional[str] = Query(setting.MINIO_BUCKET),
                  file_id: str = Query(..., description="文件id")):
    logger.info('🟢 文件下载[START]')
    minio_instance = MinioInstance(bucket_name)
    if content := minio_instance.download_minio(file_id):
        file_obj = get_file_by_id(file_id)
        file_name = file_obj.get('file_name')
        logger.info('🟢 文件下载[END]')
        return StreamingResponse(
            content,
            media_type="application/octet-stream",  # 或者根据需要设置 'image/png', 'application/pdf'
            headers={"Content-Disposition": f"attachment; filename={quote(file_name)}"}
        )
    return ApiCommonResponseDTO(message='not exist.').model_dict()


if __name__ == '__main__':
    minio_instance = MinioInstance()
    file = open('/Users/0x7o7/0x7o7_workspace/0x7o7.service/storage/商务合作合同.docx', 'rb')
    c = minio_instance.download_minio(file.name)
    print(c)
