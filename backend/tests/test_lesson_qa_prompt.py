from app.services.lesson_qa_prompt import (
    build_qa_system_prompt,
    build_qa_user_payload,
    sources_from_chunks,
)


def test_prompt_includes_cefr_and_retrieved():
    p = build_qa_system_prompt(
        cefr_level="A2",
        skill_title="Making a reservation",
        retrieved_context="[1] (Unit 3, score=0.8)\nA reservation is...",
    )
    assert "CEFR A2" in p or "A2" in p
    assert "Retrieved book context" in p
    assert "do not invent" in p.lower() or "Do not invent" in p
    assert "Making a reservation" in p
    assert "Answer ONLY using retrieved" in p
    assert "Prefer retrieved" not in p
    assert "English only" in p
    assert "Vietnamese" not in p or "no Vietnamese" in p


def test_prompt_smalltalk_skips_book_only_constraint():
    p = build_qa_system_prompt(
        cefr_level="A2",
        skill_title="Making a reservation",
        retrieved_context=None,
        force_smalltalk=True,
    )
    assert "brief friendly" in p.lower() or "acknowledgment" in p.lower()
    assert "invite" in p.lower()
    assert "Answer ONLY using the Retrieved book context" not in p
    assert "Retrieved book context:" not in p
    assert "role-play" not in p.lower()


def test_prompt_a1_a2_short_sentence_rules():
    a1 = build_qa_system_prompt(
        cefr_level="A1",
        skill_title="Greetings",
        retrieved_context=None,
    )
    assert "short" in a1.lower() or "simple" in a1.lower()

    b1 = build_qa_system_prompt(
        cefr_level="B1",
        skill_title="Greetings",
        retrieved_context=None,
    )
    assert "moderate" in b1.lower() or "everyday" in b1.lower()


def test_prompt_off_topic_redirect_not_roleplay():
    p = build_qa_system_prompt(
        cefr_level="A2",
        skill_title="Making a reservation",
        retrieved_context=None,
        force_off_topic=True,
    )
    assert "off-topic" in p.lower() or "OFF-TOPIC" in p
    assert "role-play" not in p.lower()
    assert "in character" not in p.lower()


def test_prompt_empty_retrieved_context():
    p = build_qa_system_prompt(
        cefr_level="A2",
        skill_title="Test",
        retrieved_context=None,
    )
    assert "cannot find" in p.lower() or "empty" in p.lower() or "(none)" in p


def test_user_payload_formats_transcript():
    payload = build_qa_user_payload(
        transcript=[
            {"role": "user", "content": "What does reservation mean?"},
            {"role": "assistant", "content": "A reservation is booking a table."},
            {"role": "user", "content": "Can you give an example?"},
        ]
    )
    assert "user: What does reservation mean?" in payload
    assert "assistant: A reservation is booking a table." in payload
    assert "Can you give an example?" in payload
    assert "role-play" not in payload.lower()
    assert "in character" not in payload.lower()


def test_sources_dedupe_titles():
    src = sources_from_chunks(
        [
            {"unit_title": "Unit 3", "score": 0.9},
            {"unit_title": "Unit 3", "score": 0.8},
            {"unit_title": "Unit 4", "score": 0.7},
        ]
    )
    assert [s["unit_title"] for s in src] == ["Unit 3", "Unit 4"]


def test_sources_keeps_highest_score_on_dedupe():
    src = sources_from_chunks(
        [
            {"unit_title": "Unit 3", "score": 0.8},
            {"unit_title": "Unit 3", "score": 0.9},
        ]
    )
    assert len(src) == 1
    assert src[0]["score"] == 0.9


def test_sources_max_three():
    src = sources_from_chunks(
        [
            {"unit_title": f"Unit {i}", "score": 1.0 - i * 0.1}
            for i in range(5)
        ]
    )
    assert len(src) == 3


def test_sources_skips_missing_titles():
    src = sources_from_chunks(
        [
            {"unit_title": "Unit 1", "score": 0.9},
            {"unit_title": None, "score": 0.8},
            {"unit_title": "", "score": 0.7},
            {"unit_title": "Unit 2", "score": 0.6},
        ]
    )
    assert [s["unit_title"] for s in src] == ["Unit 1", "Unit 2"]
