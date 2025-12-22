# -*- coding: utf-8 -*-
from typing import Annotated, Any
from fastapi import Request, Depends
from src.server.libs.token_lib import token_handler


def token_identify(request: Request):
    auth = request.cookies.get('access_token')
    if checkout := token_handler.verify_token(auth):
        return checkout.get('data').get('id')
    else:
        return None


TokenChecker = Annotated[Any, Depends(token_identify)]
