from collections import Counter
from math import prod

from app.domain import Candidate, Portfolio, PortfolioRequest


def _independent(candidate: Candidate, selected: list[Candidate]) -> bool:
    if any(candidate.event_id == leg.event_id for leg in selected):
        return False
    if candidate.correlation_cluster and any(
        candidate.correlation_cluster == leg.correlation_cluster for leg in selected
    ):
        return False
    return True


def _score(candidate: Candidate) -> float:
    # Confidence leads; data quality and calibrated probability break ties.
    return (
        candidate.analytical_confidence
        + candidate.data_quality * 3.0
        + candidate.calibrated_probability * 2.0
    )


def build_portfolio(request: PortfolioRequest) -> Portfolio:
    qualified = [
        c for c in request.candidates
        if c.analytical_confidence >= request.min_confidence and c.data_quality >= 0.70
    ]
    qualified.sort(key=_score, reverse=True)

    if len({c.event_id for c in qualified}) < request.min_legs:
        return Portfolio(
            status="NO_QUALIFIED_PORTFOLIO",
            reason="Insufficient independent events meeting confidence and data-quality gates.",
        )

    selected: list[Candidate] = []
    sport_counts: Counter = Counter()

    # First pass encourages diversification while retaining quality.
    for candidate in qualified:
        if len(selected) >= request.max_legs:
            break
        if not _independent(candidate, selected):
            continue
        if sport_counts[candidate.sport] >= 4:
            continue
        selected.append(candidate)
        sport_counts[candidate.sport] += 1
        odds = prod(c.decimal_odds for c in selected)
        if len(selected) >= request.min_legs and request.target_odds_min <= odds <= request.target_odds_max:
            return _complete(selected)
        if odds > request.target_odds_max:
            selected.pop()
            sport_counts[candidate.sport] -= 1

    if len(selected) >= request.min_legs:
        odds = prod(c.decimal_odds for c in selected)
        if request.target_odds_min <= odds <= request.target_odds_max:
            return _complete(selected)

    return Portfolio(
        status="NO_QUALIFIED_PORTFOLIO",
        reason="Qualified candidates could not satisfy leg-count, independence and target-odds constraints without weakening the gates.",
    )


def _complete(selected: list[Candidate]) -> Portfolio:
    odds = prod(c.decimal_odds for c in selected)
    avg_confidence = sum(c.analytical_confidence for c in selected) / len(selected)
    return Portfolio(
        status="QUALIFIED",
        legs=selected,
        combined_odds=round(odds, 4),
        average_confidence=round(avg_confidence, 2),
    )
