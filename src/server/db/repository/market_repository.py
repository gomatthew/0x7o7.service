# -*- coding: utf-8 -*-
from sqlalchemy import text

from src.server.db.crm_base import with_market_session


SOURCE_COLUMNS = """
    src.source_id AS source_id, src.canonical_url AS source_canonical_url,
    src.source_type AS source_type, src.title AS source_title,
    src.published_at AS source_published_at,
    src.last_verified_at AS source_last_verified_at,
    src.access_status AS source_access_status,
    src.fact_summary AS source_fact_summary
"""


def source_from_row(row):
    if not row.get("source_id"):
        return None
    return {
        "source_id": row["source_id"],
        "canonical_url": row["source_canonical_url"],
        "source_type": row["source_type"],
        "title": row["source_title"],
        "published_at": row["source_published_at"],
        "last_verified_at": row["source_last_verified_at"],
        "access_status": row["source_access_status"],
        "fact_summary": row["source_fact_summary"],
    }


def signal_from_row(row):
    return {
        "signal_id": row["signal_id"],
        "subject_name": row["subject_name"],
        "subject_type": row["subject_type"],
        "source_date": row["source_date"],
        "fact_description": row["fact_description"],
        "agent_inference": row["agent_inference"],
        "workflow_problem": row["workflow_problem"],
        "commercial_signal": row["commercial_signal"],
        "evidence_level": row["evidence_level"],
        "research_status": row["research_status"],
        "last_verified_at": row["last_verified_at"],
        "data_version": row["data_version"],
        "source": source_from_row(row),
        "link_type": row.get("link_type"),
    }


@with_market_session
def check_market_database(session):
    session.execute(text("SELECT 1"))
    return True


@with_market_session
def get_market_dashboard_from_db(session):
    row = session.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM market_sources) AS source_count,
          (SELECT COUNT(*) FROM market_signals) AS signal_count,
          (SELECT COUNT(*) FROM market_opportunities) AS opportunity_count,
          (SELECT COUNT(*) FROM market_opportunities WHERE research_status='qualified_opportunity') AS qualified_opportunity_count,
          (SELECT COUNT(*) FROM market_agency_candidates) AS agency_count,
          (SELECT COUNT(*) FROM market_research_briefs) AS brief_count,
          (SELECT COUNT(*) FROM market_research_runs) AS research_run_count
    """)).mappings().one()
    return dict(row)


@with_market_session
def list_market_opportunities_from_db(session):
    rows = session.execute(text(f"""
        SELECT o.opportunity_id, o.title, o.target_buyer, o.buyer_role,
               o.workflow_problem, o.commercial_signal, o.delivery_fit,
               o.evidence_level, o.research_status, o.blocking_questions,
               o.fact_description, o.agent_inference, o.source_date,
               o.first_discovered_at, o.last_verified_at, o.data_version,
               o.no_auto_outreach, {SOURCE_COLUMNS}
        FROM market_opportunities o
        LEFT JOIN market_sources src ON src.source_id=o.primary_source_id
        ORDER BY o.research_status='qualified_opportunity' DESC,
                 o.last_verified_at DESC, o.opportunity_id
    """)).mappings().all()
    return [{**dict(row), "primary_source": source_from_row(row), "linked_signals": []} for row in rows]


@with_market_session
def get_market_opportunity_from_db(session, opportunity_id):
    row = session.execute(text(f"""
        SELECT o.opportunity_id, o.title, o.target_buyer, o.buyer_role,
               o.workflow_problem, o.commercial_signal, o.delivery_fit,
               o.evidence_level, o.research_status, o.blocking_questions,
               o.fact_description, o.agent_inference, o.source_date,
               o.first_discovered_at, o.last_verified_at, o.data_version,
               o.no_auto_outreach, {SOURCE_COLUMNS}
        FROM market_opportunities o
        LEFT JOIN market_sources src ON src.source_id=o.primary_source_id
        WHERE o.opportunity_id=:opportunity_id
    """), {"opportunity_id": opportunity_id}).mappings().first()
    if not row:
        return None
    signals = session.execute(text(f"""
        SELECT s.signal_id, s.subject_name, s.subject_type, s.source_date,
               s.fact_description, s.agent_inference, s.workflow_problem,
               s.commercial_signal, s.evidence_level, s.research_status,
               s.last_verified_at, s.data_version, l.link_type, {SOURCE_COLUMNS}
        FROM market_opportunity_signal_links l
        JOIN market_signals s ON s.signal_id=l.signal_id
        JOIN market_sources src ON src.source_id=s.source_id
        WHERE l.opportunity_id=:opportunity_id
        ORDER BY FIELD(l.link_type, 'direct_demand', 'corroborating', 'disqualifying'), s.signal_id
    """), {"opportunity_id": opportunity_id}).mappings().all()
    return {**dict(row), "primary_source": source_from_row(row), "linked_signals": [signal_from_row(item) for item in signals]}


@with_market_session
def list_market_signals_from_db(session):
    rows = session.execute(text(f"""
        SELECT s.signal_id, s.subject_name, s.subject_type, s.source_date,
               s.fact_description, s.agent_inference, s.workflow_problem,
               s.commercial_signal, s.evidence_level, s.research_status,
               s.last_verified_at, s.data_version, NULL AS link_type, {SOURCE_COLUMNS}
        FROM market_signals s
        JOIN market_sources src ON src.source_id=s.source_id
        ORDER BY s.last_verified_at DESC, s.signal_id
    """)).mappings().all()
    return [signal_from_row(row) for row in rows]


@with_market_session
def get_market_signal_from_db(session, signal_id):
    row = session.execute(text(f"""
        SELECT s.signal_id, s.subject_name, s.subject_type, s.source_date,
               s.fact_description, s.agent_inference, s.workflow_problem,
               s.commercial_signal, s.evidence_level, s.research_status,
               s.last_verified_at, s.data_version, NULL AS link_type, {SOURCE_COLUMNS}
        FROM market_signals s
        JOIN market_sources src ON src.source_id=s.source_id
        WHERE s.signal_id=:signal_id
    """), {"signal_id": signal_id}).mappings().first()
    return signal_from_row(row) if row else None


@with_market_session
def list_market_agencies_from_db(session):
    rows = session.execute(text(f"""
        SELECT a.candidate_id, a.company, a.country, a.team_size,
               a.timezone_fit, a.service_match, a.fact_description,
               a.agent_inference, a.async_fit, a.research_risk,
               a.evidence_level, a.research_status, a.last_verified_at,
               a.data_version, {SOURCE_COLUMNS}
        FROM market_agency_candidates a
        JOIN market_sources src ON src.source_id=a.source_id
        ORDER BY a.research_status='qualified_opportunity' DESC,
                 a.evidence_level DESC, a.candidate_id
    """)).mappings().all()
    return [{
        "candidate_id": row["candidate_id"], "company": row["company"],
        "country": row["country"], "team_size": row["team_size"],
        "timezone_fit": row["timezone_fit"], "service_match": row["service_match"],
        "fact_description": row["fact_description"], "agent_inference": row["agent_inference"],
        "async_fit": row["async_fit"], "research_risk": row["research_risk"],
        "evidence_level": row["evidence_level"], "research_status": row["research_status"],
        "last_verified_at": row["last_verified_at"], "data_version": row["data_version"],
        "source": source_from_row(row),
    } for row in rows]


@with_market_session
def list_market_research_runs_from_db(session, limit=20):
    rows = session.execute(text("""
        SELECT run_id, started_at, completed_at, rules_version, status,
               statistics_json, no_auto_outreach, created_at
        FROM market_research_runs ORDER BY started_at DESC LIMIT :limit
    """), {"limit": int(limit)}).mappings().all()
    return [dict(row) for row in rows]


@with_market_session
def get_market_publication_from_db(session):
    publication = session.execute(text("""
        SELECT publication_id, import_id, target_name, target_schema_version,
               target_data_hash, target_row_counts_json, status, published_at,
               error_summary, created_at
        FROM market_publications ORDER BY created_at DESC LIMIT 1
    """)).mappings().first()
    research_import = session.execute(text("""
        SELECT import_id, research_run_id, data_version, schema_version,
               data_hash, row_counts_json, published_at, status, created_at
        FROM market_research_imports ORDER BY created_at DESC LIMIT 1
    """)).mappings().first()
    return {
        "publication": dict(publication) if publication else None,
        "research_import": dict(research_import) if research_import else None,
    }
