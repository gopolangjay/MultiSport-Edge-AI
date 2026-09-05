from app.sports_data import _normalise


def test_normalise_exposes_provider_team_logos():
    event = {
        "idEvent": "1",
        "strSport": "Soccer",
        "strLeague": "Test League",
        "strEvent": "Home vs Away",
        "strHomeTeam": "Home",
        "strAwayTeam": "Away",
        "idHomeTeam": "10",
        "idAwayTeam": "20",
        "strHomeTeamBadge": "https://example.test/home.png",
        "strAwayTeamBadge": "https://example.test/away.png",
        "strLeagueBadge": "https://example.test/league.png",
        "strThumb": "https://example.test/event.jpg",
    }
    row = _normalise(event)
    assert row["home_logo"] == event["strHomeTeamBadge"]
    assert row["away_logo"] == event["strAwayTeamBadge"]
    assert row["league_logo"] == event["strLeagueBadge"]
    assert row["home_team_id"] == "10"
    assert row["away_team_id"] == "20"
