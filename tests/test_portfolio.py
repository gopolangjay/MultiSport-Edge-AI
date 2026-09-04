from datetime import datetime, timezone

from app.domain import Bookmaker, Candidate, PortfolioRequest, Sport
from app.portfolio import build_portfolio


def candidate(i: int, odds: float = 1.03) -> Candidate:
    sports = list(Sport)
    return Candidate(
        id=f"c{i}",
        sport=sports[i % len(sports)],
        event_id=f"event-{i}",
        event_name=f"Event {i}",
        starts_at=datetime.now(timezone.utc),
        market="safe-market",
        selection=f"selection-{i}",
        bookmaker=Bookmaker.BETWAY,
        decimal_odds=odds,
        calibrated_probability=0.94,
        analytical_confidence=94.0,
        data_quality=0.95,
        correlation_cluster=f"event-{i}",
    )


def test_builds_qualified_portfolio_when_constraints_fit():
    items = [candidate(i, 1.04) for i in range(10)]
    result = build_portfolio(
        PortfolioRequest(
            candidates=items,
            target_odds_min=1.45,
            target_odds_max=1.50,
            min_legs=10,
            max_legs=10,
        )
    )
    assert result.status == "QUALIFIED"
    assert len(result.legs) == 10


def test_refuses_to_force_weak_candidates():
    items = [candidate(i) for i in range(9)]
    result = build_portfolio(PortfolioRequest(candidates=items))
    assert result.status == "NO_QUALIFIED_PORTFOLIO"
