from app.edge_policy import daily_funnel, optimize_safest, qualification_state


def candidate(**overrides):
    row = {
        "sport": "football",
        "event": "A vs B",
        "bookmaker": "betway",
        "market": "Goals Over 1.5",
        "selection": "Over 1.5",
        "odds": 1.04,
        "source_url": "https://www.betway.co.za/event/1",
        "evidence_sources": [
            "https://www.betway.co.za/event/1",
            "https://www.flashscore.co.za/match/1",
            "https://www.sofascore.com/game/1",
        ],
        "analytical_confidence": 93.0,
        "model_validated": True,
        "model_id": "football-goals",
        "model_version": "2.0",
    }
    row.update(overrides)
    return row


def test_odds_alone_cannot_qualify():
    state, _ = qualification_state(candidate(evidence_sources=["https://www.betway.co.za/event/1"]))
    assert state == "EVIDENCE_PENDING"


def test_one_independent_source_cannot_qualify():
    state, _ = qualification_state(candidate(evidence_sources=[
        "https://www.betway.co.za/event/1", "https://www.flashscore.co.za/match/1"
    ]))
    assert state == "EVIDENCE_PENDING"


def test_unsupported_market_cannot_qualify():
    state, _ = qualification_state(candidate(market="First throw-in"))
    assert state == "MODEL_PENDING"


def test_unvalidated_model_cannot_qualify():
    state, _ = qualification_state(candidate(model_validated=False))
    assert state == "MODEL_PENDING"


def test_below_90_cannot_qualify():
    state, _ = qualification_state(candidate(analytical_confidence=89.99))
    assert state == "BELOW_THRESHOLD"


def test_valid_independent_model_output_can_qualify():
    state, reason = qualification_state(candidate())
    assert state == "QUALIFIED"
    assert reason is None


def test_optimizer_never_fabricates_and_uses_one_leg_per_event():
    rows = []
    for i in range(15):
        rows.append(candidate(event=f"Team {i} vs Team X{i}", odds=1.03, analytical_confidence=95 - i / 10))
        rows.append(candidate(event=f"Team {i} vs Team X{i}", odds=1.02, analytical_confidence=91))
    result = optimize_safest(rows)
    assert result["status"] in {"LOCKED", "WAITING"}
    if result["status"] == "LOCKED":
        assert 10 <= len(result["legs"]) <= 15
        assert len({x["event"] for x in result["legs"]}) == len(result["legs"])
        assert 1.55 <= result["combined_odds"] <= 1.60


def test_insufficient_candidates_returns_empty_locked_legs():
    result = optimize_safest([candidate(event=f"A{i} vs B{i}") for i in range(5)])
    assert result["status"] == "WAITING"
    assert result["legs"] == []
    assert result["locked_count"] == 0


def test_daily_funnel_counts_only_locked_edge():
    events = [{"home_score": None, "away_score": None}, {"home_score": 1, "away_score": 0}]
    rows = [candidate()]
    funnel = daily_funnel(events, rows, {"status": "WAITING", "locked_count": 0})
    assert funnel["total_games_today"] == 2
    assert funnel["remaining_games"] == 1
    assert funnel["edge_locked_count"] == 0
