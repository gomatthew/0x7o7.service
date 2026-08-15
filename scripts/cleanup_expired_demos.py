#!/usr/bin/env python3
"""Delete expired flagship-demo files, indexes, and generated results."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.configs import get_setting, logger
from src.server.db.models.demo_model import DemoJobModel
from src.server.db.repository import list_expired_demo_sessions, mark_demo_session_deleted
from src.server.db.session import session_scope


def main():
    setting = get_setting()
    root = Path(setting.DEMO_UPLOAD_ROOT).resolve()
    expired = list_expired_demo_sessions(datetime.now(timezone.utc))
    for row in expired:
        path = Path(row.storage_path).resolve()
        if root in path.parents and path.is_dir():
            shutil.rmtree(path)
        with session_scope() as session:
            session.query(DemoJobModel).filter(DemoJobModel.session_id == row.id).delete()
        mark_demo_session_deleted(row.id)
        logger.info(f"Deleted expired demo session {row.id}")
    print(f"deleted={len(expired)}")


if __name__ == "__main__":
    main()
