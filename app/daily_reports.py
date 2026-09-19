"""Private, bounded original research reports; never an automatic odds feed."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app import private_store as store

SAST = ZoneInfo("Africa/Johannesburg")
router = APIRouter(prefix="/v1/research-reports")


class SourceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    url: HttpUrl
    status: Literal["checked", "partial", "unavailable", "restricted", "not_checked"]
    checked_at: AwareDatetime | None = None
    note: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def safe_source(self):
        if self.url.scheme != "https" or self.url.username or self.url.password:
            raise ValueError("Source links must use HTTPS without embedded credentials")
        if len(str(self.url)) > 1000:
            raise ValueError("Source URL too long")
        if self.status in {"checked", "partial"} and self.checked_at is None:
            raise ValueError("Checked sources require the actual observation time")
        return self


class DailyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: Literal[1] = 1
    report_date: date
    generated_at: AwareDatetime
    status: Literal["NO_QUALIFIED_PORTFOLIO", "RESEARCH_SHORTLIST", "NO_DATA"]
    summary: str = Field(min_length=1, max_length=2400)
    analysis: str = Field(min_length=1, max_length=24000)
    limitations: str = Field(min_length=1, max_length=4000)
    previous_day_review: str = Field(min_length=1, max_length=6000)
    sources: list[SourceCheck] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def chronology(self):
        if self.generated_at.astimezone(SAST).date() != self.report_date:
            raise ValueError("Report date must match the generated date in SAST")
        for source in self.sources:
            if source.checked_at and source.checked_at > self.generated_at:
                raise ValueError("Source checks cannot occur after report generation")
        return self


def publish(report: DailyReport) -> dict:
    now = datetime.now(SAST)
    if report.report_date != now.date() or report.generated_at > now + timedelta(minutes=5):
        raise HTTPException(422, "Only today's SAST report may be published; no future timestamps")
    payload = report.model_dump(mode="json")
    content_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    key = "report:" + report.report_date.isoformat()
    record = {"report": payload, "sha256": content_hash, "received_at": now.isoformat()}
    created = store.create(key, record)
    if not created:
        existing = store.get(key)
        if not existing or existing["sha256"] != content_hash:
            raise HTTPException(
                409, "A different report is already saved for this day; no overwrite"
            )
    # Acknowledge only metadata. The publisher cannot read stored private reports.
    return {
        "ok": True,
        "report_date": payload["report_date"],
        "sha256": content_hash,
        "stored": True,
        "duplicate": not created,
        "storage": "private_database",
    }


@router.get("/latest")
def latest_report():
    reports = store.recent("report:", 1)
    if not reports:
        return {
            "ok": True,
            "report": None,
            "state": "AWAITING_FIRST_REPORT",
            "schedule": "00:00 Africa/Johannesburg",
        }
    latest = reports[0]
    return {
        "ok": True,
        **latest,
        "state": "CURRENT"
        if latest["report"]["report_date"] == datetime.now(SAST).date().isoformat()
        else "OLDER_REPORT",
        "research_only": True,
        "notice": "Research does not automatically qualify a bet. Recheck odds and team news.",
    }


@router.get("")
def report_history():
    return {
        "reports": [
            {
                "report_date": x["report"]["report_date"],
                "status": x["report"]["status"],
                "received_at": x["received_at"],
            }
            for x in store.recent("report:", 31)
        ]
    }


@router.get("/{on}")
def report_on(on: date):
    record = store.get("report:" + on.isoformat())
    if not record:
        raise HTTPException(404, "Report not found")
    return {"ok": True, **record, "research_only": True}
