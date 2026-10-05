# -*- coding: utf-8 -*-
import argparse
import base64
import json
import os
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def decode_value(value):
    if not isinstance(value, dict) or set(value) != {"type", "value"}:
        return value
    if value["type"] == "datetime":
        return datetime.fromisoformat(value["value"])
    if value["type"] == "date":
        return value["value"]
    if value["type"] == "decimal":
        return Decimal(value["value"])
    if value["type"] == "bytes":
        return base64.b64decode(value["value"])
    raise ValueError(f"Unsupported snapshot value type: {value['type']}")


def import_snapshot(database_url, payload, owner_from=None, owner_to=None):
    if payload.get("format") != "0x7o7-mysql-snapshot-v1":
        raise ValueError("Unsupported snapshot format")
    engine = create_engine(database_url, pool_pre_ping=True)
    counts = {}
    try:
        schema = inspect(engine)
        with engine.begin() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            try:
                for table, encoded_rows in payload["tables"].items():
                    if not IDENTIFIER_PATTERN.fullmatch(table):
                        raise ValueError(f"Invalid table name: {table}")
                    available_columns = {column["name"] for column in schema.get_columns(table)}
                    row_columns = set(encoded_rows[0]) if encoded_rows else available_columns
                    missing_columns = row_columns - available_columns
                    if missing_columns:
                        raise RuntimeError(f"{table} is missing columns: {sorted(missing_columns)}")
                    connection.execute(text(f"DELETE FROM `{table}`"))
                    if not encoded_rows:
                        counts[table] = 0
                        continue
                    columns = list(encoded_rows[0])
                    quoted_columns = ", ".join(f"`{column}`" for column in columns)
                    placeholders = ", ".join(f":{column}" for column in columns)
                    rows = []
                    for encoded_row in encoded_rows:
                        row = {key: decode_value(value) for key, value in encoded_row.items()}
                        if owner_from is not None and owner_to is not None and row.get("owner_user_id") == owner_from:
                            row["owner_user_id"] = owner_to
                        rows.append(row)
                    connection.execute(text(f"INSERT INTO `{table}` ({quoted_columns}) VALUES ({placeholders})"), rows)
                    counts[table] = len(rows)
            finally:
                connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    finally:
        engine.dispose()
    return counts


def main():
    parser = argparse.ArgumentParser(description="Import a validated MySQL table snapshot")
    parser.add_argument("--database-url-env", required=True, help="保存数据库 URL 的环境变量名")
    parser.add_argument("--input", required=True, type=Path, help="快照输入路径")
    parser.add_argument("--owner-from", help="需要替换的 owner_user_id")
    parser.add_argument("--owner-to", help="替换后的 owner_user_id")
    args = parser.parse_args()
    database_url = os.getenv(args.database_url_env, "").strip()
    if not database_url:
        raise RuntimeError(f"{args.database_url_env} is not configured")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    counts = import_snapshot(database_url, payload, args.owner_from, args.owner_to)
    print(" ".join(f"{table}={count}" for table, count in counts.items()))


if __name__ == "__main__":
    main()
