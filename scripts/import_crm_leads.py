from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from src.server.crm_db.base import CRMSessionLocal, create_crm_tables
from src.server.crm_db.models import (
    CRMActivityModel,
    CRMCompanyModel,
    CRMContactModel,
    CRMFollowupTaskModel,
)


def clean(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def import_leads(csv_path: Path, owner_user_id: str) -> dict[str, int]:
    create_crm_tables()
    counts = {"companies": 0, "contacts": 0, "activities": 0, "followups": 0}
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with csv_path.open(newline="", encoding="utf-8") as source, CRMSessionLocal() as session:
        for row in csv.DictReader(source):
            website = clean(row.get("website"))
            company = session.scalar(
                select(CRMCompanyModel).where(
                    CRMCompanyModel.owner_user_id == owner_user_id,
                    CRMCompanyModel.website == website,
                )
            )
            if company is None:
                company = CRMCompanyModel(
                    owner_user_id=owner_user_id,
                    name=row["company_name"].strip(),
                    website=website,
                    country=clean(row.get("country")) or "US",
                    industry=clean(row.get("segment")),
                    employee_band=clean(row.get("employee_band")),
                    fit_score=int(clean(row.get("fit_score")) or 50),
                    status=clean(row.get("status")) or "researching",
                    source_url=clean(row.get("company_source_url")),
                    buying_signal=clean(row.get("buying_signal")),
                    value_hypothesis=clean(row.get("value_hypothesis")),
                    notes=clean(row.get("company_notes")),
                )
                session.add(company)
                session.flush()
                counts["companies"] += 1

            full_name = row["full_name"].strip()
            contact = session.scalar(
                select(CRMContactModel).where(
                    CRMContactModel.owner_user_id == owner_user_id,
                    CRMContactModel.company_id == company.id,
                    CRMContactModel.full_name == full_name,
                )
            )
            if contact is None:
                contact = CRMContactModel(
                    owner_user_id=owner_user_id,
                    company_id=company.id,
                    full_name=full_name,
                    role=clean(row.get("role")),
                    email=clean(row.get("email")),
                    linkedin_url=clean(row.get("linkedin_url")),
                    platform=clean(row.get("platform")),
                    platform_profile_url=clean(row.get("platform_profile_url")),
                    preferred_channel=clean(row.get("preferred_channel")),
                    verification_status=clean(row.get("verification_status")) or "unverified",
                    source_url=clean(row.get("contact_source_url")),
                    notes=clean(row.get("contact_notes")),
                )
                session.add(contact)
                session.flush()
                counts["contacts"] += 1

            research_summary = f"已完成首轮公开资料研究：{company.name}"
            activity = session.scalar(
                select(CRMActivityModel).where(
                    CRMActivityModel.owner_user_id == owner_user_id,
                    CRMActivityModel.company_id == company.id,
                    CRMActivityModel.summary == research_summary,
                )
            )
            if activity is None:
                session.add(
                    CRMActivityModel(
                        owner_user_id=owner_user_id,
                        company_id=company.id,
                        contact_id=contact.id,
                        activity_type="research",
                        direction="internal",
                        summary=research_summary,
                        outcome="已保存公开购买信号与价值假设，尚未外联",
                        happened_at=now,
                    )
                )
                counts["activities"] += 1

            followup_description = f"核实 {company.name} 的官方域名与直接商务联系方式"
            followup = session.scalar(
                select(CRMFollowupTaskModel).where(
                    CRMFollowupTaskModel.owner_user_id == owner_user_id,
                    CRMFollowupTaskModel.contact_id == contact.id,
                    CRMFollowupTaskModel.description == followup_description,
                )
            )
            if followup is None:
                session.add(
                    CRMFollowupTaskModel(
                        owner_user_id=owner_user_id,
                        contact_id=contact.id,
                        due_at=now + timedelta(days=7),
                        task_type="research",
                        description=followup_description,
                    )
                )
                counts["followups"] += 1

        session.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import researched leads into the CRM database")
    parser.add_argument("--csv", type=Path, default=Path("data/crm_initial_leads.csv"))
    parser.add_argument("--owner-id", required=True, help="Existing administrator user id")
    args = parser.parse_args()
    counts = import_leads(args.csv, str(args.owner_id))
    print("CRM import complete: " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
