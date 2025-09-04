# -*- coding: utf-8 -*-
from sqlalchemy import Column, DateTime, String, func, Text
from sqlalchemy.dialects.postgresql import UUID
from src.server.db.base import Base


class FileModel(Base):
    """
    文件记录模型
    """

    __tablename__ = "file"
    id = Column(String(64), primary_key=True, comment="文件ID")
    file_name = Column(String(256), comment="文件名")
    file_path = Column(String(256), comment="文件路径")
    meta_data = Column(String(512), comment='meta')
    file_extension = Column(String(16), comment="文件后缀")
    # created_org_id = Column(String(64), comment="创建人组织ID")
    # created_org_name = Column(String(32), comment="创建人组织名称")
    created_user_id = Column(String(64), comment="创建人ID")
    created_user_name = Column(String(32), comment="创建人名称")
    created_time = Column(DateTime, default=func.now(), comment="创建时间")
    status = Column(String(2), default='1', comment="文件状态，0-已删除，1-有效")

    def __repr__(self):
        return f"<File(id='{self.id}', name='{self.file_name}',create_time='{self.created_time}')>"
