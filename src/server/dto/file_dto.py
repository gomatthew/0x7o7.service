# -*- coding: utf-8 -*-
from typing import Any, Optional, Union
from pydantic import BaseModel, Field


class AddFileToDBDTO(BaseModel):
    file_id: Optional[str] = None
    file_name: str = None
    file_path: str = None
    meta_data: str = None
    file_extension: str = None
    biz_type: str = None
    created_user_id: str = None
    created_user_name: Optional[str] = None
    created_time: Optional[str] = None
    status: Union[str, int] = 1
