# -*- coding: utf-8 -*-
import bcrypt


class BcryptLib:
    @staticmethod
    def hash_password(plain_password: str) -> str:
        # 生成盐并哈希密码（默认 cost 为 12，够安全）
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


bp = BcryptLib()
