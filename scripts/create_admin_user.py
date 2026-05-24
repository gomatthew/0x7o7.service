# -*- coding: utf-8 -*-
import os
import secrets

from src.configs import get_setting
from src.server.db.models import UserModel
from src.server.db.session import session_scope
from src.server.libs import bp

setting = get_setting()


def main():
    email = os.getenv("ADMIN_EMAIL", "admin@0x7o7.local").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or f"Admin-{secrets.token_urlsafe(18)}"
    nickname = os.getenv("ADMIN_NICKNAME", "0x7o7 Admin")
    tenant_id = os.getenv("ADMIN_TENANT_ID", "admin")

    with session_scope() as session:
        user = session.query(UserModel).filter(UserModel.mail == email).first()
        if user is None:
            user = UserModel(
                tenant_id=tenant_id,
                user_nick_name=nickname,
                mail=email,
                phone_number=None,
                password=bp.hash_password(password),
                role=setting.ADMIN_ROLE,
                created_user="admin_seed",
            )
            session.add(user)
            action = "created"
        else:
            user.tenant_id = user.tenant_id or tenant_id
            user.user_nick_name = user.user_nick_name or nickname
            user.password = bp.hash_password(password)
            user.role = setting.ADMIN_ROLE
            user.status = 1
            session.add(user)
            action = "updated"
        session.flush()
        user_id = user.id

    print(f"admin_user_{action}=true")
    print(f"user_id={user_id}")
    print(f"email={email}")
    print(f"password={password}")
    print(f"role={setting.ADMIN_ROLE}")


if __name__ == "__main__":
    main()
