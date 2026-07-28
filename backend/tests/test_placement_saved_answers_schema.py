from app.schemas.onboarding_schema import PlacementSessionData


def test_session_schema_includes_saved_answers():
    data = PlacementSessionData(
        done=False,
        attempt_id=1,
        section="reading",
        saved_answers={"12": "will review", "15": "by"},
    )
    assert data.saved_answers["12"] == "will review"
