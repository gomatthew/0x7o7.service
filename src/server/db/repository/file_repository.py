# -*- coding: utf-8 -*-
import uuid

from src.server.db import session
from src.server.db.session import with_session
from src.server.db.models.file_model import FileModel
from src.server.dto.file_dto import AddFileToDBDTO


@with_session
def add_file_to_db(session, file_dto: AddFileToDBDTO):
    new_file_orm = FileModel()
    new_file_orm.id = file_dto.file_id if file_dto.file_id else uuid.uuid4().hex
    new_file_orm.file_name = file_dto.file_name
    new_file_orm.file_path = file_dto.file_path
    new_file_orm.meta_data = file_dto.meta_data
    new_file_orm.file_extension = file_dto.file_extension
    new_file_orm.created_user_id = file_dto.created_user_id
    new_file_orm.created_user_name = file_dto.created_user_name
    session.add(new_file_orm)
    session.commit()


@with_session
def get_file_by_id(session, file_id: str):
    if q := session.query(FileModel).filter(FileModel.id == file_id).one():
        return {'file_name': q.file_name}
    else:
        return None
