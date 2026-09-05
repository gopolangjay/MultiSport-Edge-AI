"""Persistent storage for sourced web-intelligence observations.

Uses Render Postgres when DATABASE_URL is configured and falls back to process memory
for local development. Only sourced observations are stored; qualification remains in
web_pipeline.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from threading import RLock
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text

SAST = ZoneInfo("Africa/Johannesburg")
MAX_AGE = timedelta(hours=2)
_LOCK = RLock()
_MEMORY: dict[str, dict] = {}
_ENGINE = None


def _key(r: dict) -> str:
    return "|".join(str(r.get(k, "")).strip().lower() for k in ("sport", "event", "bookmaker", "market", "selection"))


def _engine():
    global _ENGINE
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if _ENGINE is None:
        _ENGINE = create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2)
        with _ENGINE.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS web_observations (
                    record_key TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    observed_at TIMESTAMPTZ NOT NULL,
                    ingested_at TIMESTAMPTZ NOT NULL
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_web_observations_observed_at ON web_observations(observed_at DESC)"))
    return _ENGINE


def ingest(records: list[dict]) -> dict:
    now = datetime.now(SAST)
    valid: list[tuple[str, dict, datetime]] = []
    for raw in records:
        if not raw.get("source_url") or not raw.get("observed_at"):
            continue
        try:
            observed = datetime.fromisoformat(str(raw["observed_at"]).replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=SAST)
        except Exception:
            continue
        if now.astimezone(observed.tzinfo) - observed > MAX_AGE:
            continue
        item = dict(raw)
        item["ingested_at"] = now.isoformat()
        valid.append((_key(item), item, observed))

    engine = _engine()
    if engine is None:
        with _LOCK:
            for key, item, _ in valid:
                _MEMORY[key] = item
            _prune_memory(now)
            stored = len(_MEMORY)
    else:
        cutoff = now - MAX_AGE
        with engine.begin() as conn:
            for key, item, observed in valid:
                conn.execute(text("""
                    INSERT INTO web_observations(record_key,payload,observed_at,ingested_at)
                    VALUES (:key,CAST(:payload AS JSONB),:observed,:ingested)
                    ON CONFLICT(record_key) DO UPDATE SET
                      payload=EXCLUDED.payload,
                      observed_at=EXCLUDED.observed_at,
                      ingested_at=EXCLUDED.ingested_at
                """), {"key": key, "payload": json.dumps(item), "observed": observed, "ingested": now})
            conn.execute(text("DELETE FROM web_observations WHERE observed_at < :cutoff"), {"cutoff": cutoff})
            stored = conn.execute(text("SELECT COUNT(*) FROM web_observations")).scalar_one()
    return {"ok": True, "accepted": len(valid), "stored": stored, "storage": "postgres" if engine else "memory", "ingested_at": now.isoformat()}


def _prune_memory(now: datetime) -> None:
    stale = []
    for key, row in _MEMORY.items():
        try:
            observed = datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=SAST)
            if now.astimezone(observed.tzinfo) - observed > MAX_AGE:
                stale.append(key)
        except Exception:
            stale.append(key)
    for key in stale:
        _MEMORY.pop(key, None)


def records() -> list[dict]:
    now = datetime.now(SAST)
    engine = _engine()
    if engine is None:
        with _LOCK:
            _prune_memory(now)
            return list(_MEMORY.values())
    cutoff = now - MAX_AGE
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM web_observations WHERE observed_at < :cutoff"), {"cutoff": cutoff})
        rows = conn.execute(text("SELECT payload FROM web_observations ORDER BY observed_at DESC LIMIT 500")).scalars().all()
    return [dict(row) for row in rows]
