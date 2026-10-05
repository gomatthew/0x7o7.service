# -*- coding: utf-8 -*-
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError


MARKET_TEST_URL = os.getenv("CRM_MARKET_READONLY_TEST_URL", "").strip()
pytestmark = pytest.mark.skipif(not MARKET_TEST_URL, reason="CRM_MARKET_READONLY_TEST_URL is not configured")


@pytest.fixture(scope="module")
def market_engine():
    engine = create_engine(MARKET_TEST_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


def test_real_market_snapshot_and_opportunity_detail(market_engine):
    with market_engine.connect() as connection:
        metrics = connection.execute(text("""
            SELECT
              (SELECT COUNT(*) FROM market_sources) AS source_count,
              (SELECT COUNT(*) FROM market_signals) AS signal_count,
              (SELECT COUNT(*) FROM market_opportunities) AS opportunity_count,
              (SELECT COUNT(*) FROM market_opportunities WHERE research_status='qualified_opportunity') AS qualified_count,
              (SELECT COUNT(*) FROM market_agency_candidates) AS agency_count
        """)).mappings().one()
        assert dict(metrics) == {
            "source_count": 36,
            "signal_count": 26,
            "opportunity_count": 7,
            "qualified_count": 4,
            "agency_count": 10,
        }
        detail = connection.execute(text("""
            SELECT o.opportunity_id, o.primary_source_id, COUNT(l.signal_id) AS linked_signal_count
            FROM market_opportunities o
            LEFT JOIN market_opportunity_signal_links l ON l.opportunity_id=o.opportunity_id
            WHERE o.primary_source_id IS NOT NULL
            GROUP BY o.opportunity_id, o.primary_source_id
            ORDER BY linked_signal_count DESC LIMIT 1
        """)).mappings().one()
        assert detail["primary_source_id"]
        assert detail["linked_signal_count"] > 0


def test_market_account_cannot_write(market_engine):
    with pytest.raises(DBAPIError):
        with market_engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO market_sources
                  (source_id, canonical_url, source_type, access_status, last_verified_at)
                VALUES
                  (:source_id, :canonical_url, :source_type, :access_status, NOW())
            """), {
                "source_id": "CRM-READONLY-PROBE",
                "canonical_url": "https://invalid.example/readonly-probe",
                "source_type": "test",
                "access_status": "test",
            })
