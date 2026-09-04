from __future__ import annotations

from dataclasses import dataclass

from app.domain import Candidate


@dataclass(frozen=True)
class RiskAssessment:
    allowed: bool
    penalty: float
    reasons: tuple[str, ...]


def assess_candidate(candidate: Candidate, selected: list[Candidate]) -> RiskAssessment:
    reasons: list[str] = []
    penalty = 0.0
    if any(candidate.event_id == leg.event_id for leg in selected):
        reasons.append("same_event")
        return RiskAssessment(False, 1.0, tuple(reasons))
    if candidate.correlation_cluster and any(
        candidate.correlation_cluster == leg.correlation_cluster for leg in selected
    ):
        reasons.append("correlation_cluster")
        return RiskAssessment(False, 1.0, tuple(reasons))
    same_sport = sum(1 for leg in selected if leg.sport == candidate.sport)
    if same_sport >= 4:
        reasons.append("sport_concentration")
        return RiskAssessment(False, 1.0, tuple(reasons))
    penalty += same_sport * 0.03
    return RiskAssessment(True, penalty, tuple(reasons))
