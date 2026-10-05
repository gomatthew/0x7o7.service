# -*- coding: utf-8 -*-
"""Import the legacy local SQLite CRM into the redesigned MySQL-backed CRM."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from src.server.db.crm_base import CRM_DATABASE_URL, CRMSessionLocal, create_crm_tables
from src.server.db.models.crm_model import (
    CRMActivityModel,
    CRMCompanyModel,
    CRMContactModel,
    CRMFollowupTaskModel,
    CRMOutreachDraftModel,
)


def as_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def migrate(source_db: Path, owner_user_id: str) -> dict[str, int]:
    if not CRM_DATABASE_URL.startswith("mysql"):
        raise RuntimeError("CRM_DATABASE_URL must be a MySQL URL for this migration")
    if not source_db.is_file():
        raise FileNotFoundError(source_db)

    create_crm_tables()
    source = sqlite3.connect(source_db)
    source.row_factory = sqlite3.Row
    counts = {
        "companies": 0,
        "contacts": 0,
        "outreach_drafts": 0,
        "activities": 0,
        "followups": 0,
    }

    try:
        with CRMSessionLocal() as session:
            company_ids: dict[int, int] = {}
            contact_ids: dict[int, int] = {}

            for row in source.execute("SELECT * FROM companies ORDER BY id"):
                record = session.scalar(
                    select(CRMCompanyModel).where(
                        CRMCompanyModel.owner_user_id == owner_user_id,
                        CRMCompanyModel.website == row["website"],
                    )
                )
                if record is None:
                    record = CRMCompanyModel(
                        owner_user_id=owner_user_id,
                        name=row["name"],
                        website=row["website"],
                        country=row["country"],
                        industry=row["segment"],
                        employee_band=row["employee_band"],
                        fit_score=row["fit_score"] or 50,
                        status=row["status"],
                        source_url=row["source_url"],
                        buying_signal=row["buying_signal"],
                        value_hypothesis=row["value_hypothesis"],
                        notes=row["notes"],
                        created_at=as_datetime(row["created_at"]),
                        updated_at=as_datetime(row["updated_at"]),
                    )
                    session.add(record)
                    session.flush()
                    counts["companies"] += 1
                company_ids[row["id"]] = record.id

            for row in source.execute("SELECT * FROM contacts ORDER BY id"):
                target_company_id = company_ids[row["company_id"]]
                record = session.scalar(
                    select(CRMContactModel).where(
                        CRMContactModel.owner_user_id == owner_user_id,
                        CRMContactModel.company_id == target_company_id,
                        CRMContactModel.full_name == (row["full_name"] or "未确认"),
                    )
                )
                if record is None:
                    record = CRMContactModel(
                        owner_user_id=owner_user_id,
                        company_id=target_company_id,
                        full_name=row["full_name"] or "未确认",
                        role=row["role"],
                        email=row["email"],
                        linkedin_url=row["linkedin_url"],
                        platform=row["platform"],
                        platform_profile_url=row["platform_profile_url"],
                        preferred_channel=row["preferred_channel"],
                        verification_status=row["verification_status"],
                        source_url=row["source_url"],
                        notes=row["notes"],
                        created_at=as_datetime(row["created_at"]),
                        updated_at=as_datetime(row["updated_at"]),
                    )
                    session.add(record)
                    session.flush()
                    counts["contacts"] += 1
                contact_ids[row["id"]] = record.id

            for row in source.execute("SELECT * FROM outreach_drafts ORDER BY id"):
                target_contact_id = contact_ids[row["contact_id"]]
                record = session.scalar(
                    select(CRMOutreachDraftModel).where(
                        CRMOutreachDraftModel.owner_user_id == owner_user_id,
                        CRMOutreachDraftModel.contact_id == target_contact_id,
                        CRMOutreachDraftModel.channel == row["channel"],
                        CRMOutreachDraftModel.body == row["body"],
                    )
                )
                if record is None:
                    record = CRMOutreachDraftModel(
                        owner_user_id=owner_user_id,
                        contact_id=target_contact_id,
                        channel=row["channel"],
                        subject=row["subject"],
                        body=row["body"],
                        status=row["status"],
                        approval_note=row["approval_note"],
                        approved_by=row["approved_by"],
                        approved_at=as_datetime(row["approved_at"]),
                        sent_at=as_datetime(row["sent_at"]),
                        external_message_id=row["external_message_id"],
                        created_at=as_datetime(row["created_at"]),
                        updated_at=as_datetime(row["updated_at"]),
                    )
                    session.add(record)
                    counts["outreach_drafts"] += 1

            for row in source.execute("SELECT * FROM interactions ORDER BY id"):
                summary = row["summary"]
                record = session.scalar(
                    select(CRMActivityModel).where(
                        CRMActivityModel.owner_user_id == owner_user_id,
                        CRMActivityModel.contact_id == contact_ids.get(row["contact_id"]),
                        CRMActivityModel.summary == summary,
                        CRMActivityModel.happened_at == as_datetime(row["occurred_at"]),
                    )
                )
                if record is None:
                    session.add(CRMActivityModel(
                        owner_user_id=owner_user_id,
                        company_id=company_ids.get(source.execute(
                            "SELECT company_id FROM contacts WHERE id = ?", (row["contact_id"],)
                        ).fetchone()["company_id"]),
                        contact_id=contact_ids.get(row["contact_id"]),
                        activity_type=row["channel"],
                        direction=row["direction"],
                        summary=summary,
                        outcome=row["outcome"],
                        happened_at=as_datetime(row["occurred_at"]),
                        next_followup_at=as_datetime(row["next_followup_at"]),
                        created_at=as_datetime(row["created_at"]),
                    ))
                    counts["activities"] += 1

            for row in source.execute("SELECT * FROM followup_tasks ORDER BY id"):
                target_contact_id = contact_ids.get(row["contact_id"])
                record = session.scalar(
                    select(CRMFollowupTaskModel).where(
                        CRMFollowupTaskModel.owner_user_id == owner_user_id,
                        CRMFollowupTaskModel.contact_id == target_contact_id,
                        CRMFollowupTaskModel.due_at == as_datetime(row["due_at"]),
                        CRMFollowupTaskModel.description == row["description"],
                    )
                )
                if record is None:
                    session.add(CRMFollowupTaskModel(
                        owner_user_id=owner_user_id,
                        contact_id=target_contact_id,
                        due_at=as_datetime(row["due_at"]),
                        task_type=row["task_type"],
                        description=row["description"],
                        status=row["status"],
                        completed_at=as_datetime(row["completed_at"]),
                        created_at=as_datetime(row["created_at"]),
                    ))
                    counts["followups"] += 1

            session.commit()
    finally:
        source.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--owner-id", required=True)
    args = parser.parse_args()
    counts = migrate(args.source_db, str(args.owner_id))
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
