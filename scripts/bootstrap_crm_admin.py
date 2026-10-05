# -*- coding: utf-8 -*-
from __future__ import annotations

import secrets

from sqlalchemy import select

from src.configs import get_setting
from src.server.db.base import SessionLocal
from src.server.db.models.user_model import UserModel
from src.server.libs import bp


def bootstrap_admin() -> int:
    setting = get_setting()
    email = setting.RECEIVER.strip().lower()
    if not email or "@" not in email:
        raise RuntimeError("LEAD_NOTIFICATION_EMAIL must contain the CRM owner email")

    with SessionLocal() as session:
        user = session.scalar(select(UserModel).where(UserModel.mail == email))
        if user is None:
            user = UserModel(
                user_nick_name="CRM Owner",
                phone_number=None,
                mail=email,
                password=bp.hash_password(secrets.token_urlsafe(32)),
                role=setting.ADMIN_ROLE,
                status=1,
                created_user="crm-bootstrap",
            )
            session.add(user)
            session.flush()
        else:
            user.role = setting.ADMIN_ROLE
            user.status = 1
        session.commit()
        return int(user.id)


def main() -> None:
    owner_id = bootstrap_admin()
    print(f"crm_owner_id={owner_id}")


if __name__ == "__main__":
    main()
