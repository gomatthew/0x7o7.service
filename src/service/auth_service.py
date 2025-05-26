from fastapi import Body


async def user_login(username: str = Body(..., description="用户名"), password: str = Body(..., description="密码")):
    if username == '0x7o7' and password == 'root':
        return "SUCCESS"
    else:
        return "FAIL"
