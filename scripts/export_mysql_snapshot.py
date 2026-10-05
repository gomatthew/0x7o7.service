# -*- coding: utf-8 -*-
import argparse
import base64
import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text


IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def encode_value(value):
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.isoformat(sep=" ")}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, bytes):
        return {"type": "bytes", "value": base64.b64encode(value).decode("ascii")}
    return value


def export_snapshot(database_url, tables):
    engine = create_engine(database_url, pool_pre_ping=True)
    payload = {"format": "0x7o7-mysql-snapshot-v1", "tables": {}}
    try:
        with engine.connect() as connection:
            for table in tables:
                if not IDENTIFIER_PATTERN.fullmatch(table):
                    raise ValueError(f"Invalid table name: {table}")
                rows = connection.execute(text(f"SELECT * FROM `{table}`")).mappings().all()
                payload["tables"][table] = [
                    {key: encode_value(value) for key, value in row.items()}
                    for row in rows
                ]
    finally:
        engine.dispose()
    return payload


def main():
    parser = argparse.ArgumentParser(description="Export selected MySQL tables without embedding database credentials")
    parser.add_argument("--database-url-env", required=True, help="保存数据库 URL 的环境变量名")
    parser.add_argument("--table", action="append", required=True, dest="tables", help="需要导出的表，可重复")
    parser.add_argument("--output", required=True, type=Path, help="快照输出路径")
    args = parser.parse_args()
    database_url = os.getenv(args.database_url_env, "").strip()
    if not database_url:
        raise RuntimeError(f"{args.database_url_env} is not configured")
    payload = export_snapshot(database_url, args.tables)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("snapshot=" + str(args.output) + " " + " ".join(
        f"{table}={len(rows)}" for table, rows in payload["tables"].items()
    ))


if __name__ == "__main__":
    main()
