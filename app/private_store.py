"""Durable private state. Never fall back to process memory in production."""

from __future__ import annotations

import os
import time
from functools import lru_cache
from threading import RLock

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    select,
)
from sqlalchemy.exc import IntegrityError

metadata = MetaData()
entries = Table(
    "edge_private_state",
    metadata,
    Column("key", String(192), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("expires_at", BigInteger, nullable=True, index=True),
)
_lock = RLock()


@lru_cache(maxsize=1)
def _engine_for(url: str):
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    if not url.startswith("postgresql+psycopg://"):
        if not (
            url.startswith("sqlite:///")
            and os.getenv("EDGE_TEST_SQLITE") == "1"
            and not os.getenv("RENDER")
        ):
            raise RuntimeError("A persistent Postgres database is required")
    engine = create_engine(url, pool_pre_ping=True)
    metadata.create_all(engine)
    return engine


def engine():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("Private storage is not configured")
    with _lock:
        return _engine_for(url)


def get(key: str) -> dict | None:
    with engine().connect() as conn:
        row = conn.execute(select(entries).where(entries.c.key == key)).mappings().first()
    if not row or (row["expires_at"] is not None and row["expires_at"] <= time.time()):
        return None
    return dict(row["payload"])


def create(key: str, payload: dict, expires_at: int | None = None) -> bool:
    """Insert once. Database uniqueness, not a process lock, decides ownership."""
    try:
        with engine().begin() as conn:
            conn.execute(entries.insert().values(key=key, payload=payload, expires_at=expires_at))
        return True
    except IntegrityError:
        return False


def replace(key: str, payload: dict) -> None:
    with engine().begin() as conn:
        conn.execute(entries.update().where(entries.c.key == key).values(payload=payload))


def consume(key: str) -> dict | None:
    """Single-use, atomic deletion prevents concurrent authorization-code replay."""
    with engine().begin() as conn:
        row = (
            conn.execute(delete(entries).where(entries.c.key == key).returning(entries))
            .mappings()
            .first()
        )
    if not row or (row["expires_at"] is not None and row["expires_at"] <= time.time()):
        return None
    return dict(row["payload"])


def remove_prefix(prefix: str) -> None:
    with engine().begin() as conn:
        conn.execute(delete(entries).where(entries.c.key.startswith(prefix)))


def recent(prefix: str, limit: int = 31) -> list[dict]:
    with engine().connect() as conn:
        rows = (
            conn.execute(
                select(entries)
                .where(entries.c.key.startswith(prefix))
                .order_by(entries.c.key.desc())
                .limit(limit)
            )
            .mappings()
            .all()
        )
    return [
        dict(r["payload"]) for r in rows if r["expires_at"] is None or r["expires_at"] > time.time()
    ]


def prune() -> None:
    with engine().begin() as conn:
        conn.execute(delete(entries).where(entries.c.expires_at <= int(time.time())))
