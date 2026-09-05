from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _events_payload():
    return {
        "ok": True,
        "provider": "test-provider",
        "count": 1,
        "events": [{"sport": "football", "event": "Alpha vs Beta"}],
    }


def _scan_payload():
    return {
        "observed_records": 0,
        "qualified_records": 0,
        "portfolio": {"status": "NO_QUALIFIED_PORTFOLIO"},
        "records": [],
        "generated_at": "2026-09-05T12:00:00+02:00",
        "freshness_window_minutes": 120,
        "note": "test",
    }


def test_health_endpoint():
    with patch("app.main.web_scan_snapshot", return_value=_scan_payload()):
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "multisport-edge-ai"
    assert body["stored_observations"] == 0


def test_events_today_endpoint():
    with patch("app.main.events_for_day", new=AsyncMock(return_value=_events_payload())):
        response = client.get("/v1/events/today")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_system_status_endpoint():
    with (
        patch("app.main.web_scan_snapshot", return_value=_scan_payload()),
        patch("app.main.events_for_day", new=AsyncMock(return_value=_events_payload())),
    ):
        response = client.get("/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["events_provider"]["events"] == 1
    assert body["model_gate"]["threshold"] == 90
    assert body["degraded"] is True


def test_web_intelligence_scan_endpoint():
    with patch("app.main.web_scan_snapshot", return_value=_scan_payload()):
        response = client.get("/v1/web-intelligence/scan")
    assert response.status_code == 200
    assert response.json()["qualified_records"] == 0


def test_market_collector_endpoint():
    collection = {
        "ok": True,
        "observed_at": "2026-09-05T12:00:00+02:00",
        "sources": {},
        "collected": 0,
        "ingestion": {"ok": True, "accepted": 0},
        "qualification_note": "test",
    }
    with (
        patch("app.main.collect_public_markets", new=AsyncMock(return_value=collection)),
        patch("app.main.web_scan_snapshot", return_value=_scan_payload()),
        patch("app.main.events_for_day", new=AsyncMock(return_value=_events_payload())),
    ):
        response = client.get("/v1/market-collector/run")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["collection"]["collected"] == 0
    assert body["events"]["count"] == 1
