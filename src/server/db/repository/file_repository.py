# -*- coding: utf-8 -*-
import uuid
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import insert
from src.configs import get_setting
from src.server.db.session import with_session
from src.server.db.models.file_model import FileModel
from src.server.dto.file_dto import AddFileToDBDTO

setting = get_setting()


@with_session
def check_file_count(session, kb_id: str):
    if session.query(FileModel).filter(FileModel.biz_id == kb_id).count() >= setting.DIFY_UPLOAD_FILE_LIMIT:
        # return True
        return False
    else:
        return False


@with_session
def add_file_to_db(session, file_dto: AddFileToDBDTO):
    stmt = insert(FileModel).values(
        id=file_dto.file_id or uuid.uuid4().hex,
        file_name=file_dto.file_name,
        file_path=file_dto.file_path,
        biz_type=str(file_dto.biz_type),
        biz_id=file_dto.biz_id,
        meta_data=file_dto.meta_data,
        file_extension=file_dto.file_extension,
        created_user_id=file_dto.created_user_id,
        created_user_name=file_dto.created_user_name,
    ).prefix_with("IGNORE")

    session.execute(stmt)
    session.commit()


@with_session
def get_file_by_id(session, file_id: str):
    if q := session.query(FileModel).filter(FileModel.id == file_id).one():
        return {'file_name': q.file_name}
    else:
        return None


@with_session
def get_file_list_from_db(session, kb_id: str):
    if q := session.query(FileModel).filter(FileModel.biz_id == kb_id).order_by(desc(FileModel.created_time)).all():
        return [{'file_name': _q.file_name, 'file_id': _q.id, 'batch': _q.meta_data.get('batch')} for _q in q]
    else:
        return None
