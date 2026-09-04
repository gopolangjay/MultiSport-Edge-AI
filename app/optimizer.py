from __future__ import annotations

from dataclasses import dataclass
from math import prod

from app.domain import Candidate, Portfolio, PortfolioRequest
from app.risk import assess_candidate


@dataclass
class State:
    legs: list[Candidate]
    score: float

    @property
    def odds(self) -> float:
        return prod(x.decimal_odds for x in self.legs)


def _quality(candidate: Candidate) -> float:
    return candidate.analytical_confidence + 4 * candidate.data_quality + 3 * candidate.calibrated_probability


def optimize_portfolio(request: PortfolioRequest, beam_width: int = 250) -> Portfolio:
    candidates = [c for c in request.candidates if c.analytical_confidence >= request.min_confidence and c.data_quality >= .70]
    candidates.sort(key=_quality, reverse=True)
    beam = [State([], 0.0)]
    best: State | None = None
    for candidate in candidates:
        expanded = list(beam)
        for state in beam:
            if len(state.legs) >= request.max_legs:
                continue
            risk = assess_candidate(candidate, state.legs)
            if not risk.allowed:
                continue
            legs = state.legs + [candidate]
            odds = prod(x.decimal_odds for x in legs)
            if odds > request.target_odds_max:
                continue
            score = state.score + _quality(candidate) - risk.penalty * 10
            next_state = State(legs, score)
            expanded.append(next_state)
            if len(legs) >= request.min_legs and request.target_odds_min <= odds <= request.target_odds_max:
                if best is None or next_state.score > best.score:
                    best = next_state
        expanded.sort(key=lambda s: (len(s.legs), s.score), reverse=True)
        beam = expanded[:beam_width]
    if best is None:
        return Portfolio(status="NO_QUALIFIED_PORTFOLIO", reason="No independent qualified combination satisfies the requested leg count and target odds band.")
    avg = sum(x.analytical_confidence for x in best.legs) / len(best.legs)
    return Portfolio(status="QUALIFIED", legs=best.legs, combined_odds=round(best.odds, 4), average_confidence=round(avg, 2))
