from unittest.mock import patch

import pytest

from app.services.lesson_content_validate import normalize_content, target_bounds
from app.services.lesson_generation_service import (
    _build_system_prompt,
    content_and_meta_from_llm_payload,
)


def test_system_prompt_includes_skill_guidance_and_cefr():
    min_t, max_t = target_bounds()
    grammar = _build_system_prompt(skill_type="grammar", cefr="A2")
    assert "grammar" in grammar.lower()
    assert "A2" in grammar
    assert "Vietnamese" in grammar or "English→English" in grammar or "English only" in grammar
    assert f"{min_t}-{max_t} targets" in grammar
    assert "form" in grammar
    assert "40-100" in grammar or "40–100" in grammar
    reading = _build_system_prompt(skill_type="reading", cefr="B1")
    assert "passage" in reading.lower()
    assert "B1" in reading


def _valid_payload(*, n_targets: int = 5) -> dict:
    surfaces = [
        ("drinks", "takes a drink of"),
        ("coffee", "a hot brown drink"),
        ("every morning", "each morning"),
        ("before work", "earlier than work time"),
        ("Tom", "a man's name"),
        ("work", "a job"),
        ("morning", "early part of day"),
    ]
    return {
        "title": "Morning coffee",
        "objective": "You can talk about drinks.",
        "passage": {"text": "Tom drinks coffee every morning before work."},
        "targets": [
            {"surface": s, "gloss": g} for s, g in surfaces[:n_targets]
        ],
        "checks": [
            {
                "type": "mcq",
                "prompt": "What does drinks mean here?",
                "options": ["takes a drink of", "eats", "sleeps"],
                "answer": "takes a drink of",
            },
        ],
        "writing": {
            "prompt": "Write two sentences about your morning.",
            "min_words": 12,
            "must_use": ["drinks", "every morning"],
        },
    }


def test_normalize_llm_shaped_payload():
    content = normalize_content(_valid_payload())
    assert len(content["targets"]) == 5
    assert len(content["checks"]) == 1
    assert content["targets"][0]["gloss"] == "takes a drink of"


def test_content_and_meta_rejects_too_few_targets():
    bad = _valid_payload(n_targets=2)
    with pytest.raises(ValueError, match="targets"):
        content_and_meta_from_llm_payload(bad, skill_title="X")


def test_min_targets_setting_allows_fewer():
    payload = _valid_payload(n_targets=2)
    with patch("app.services.lesson_content_validate.settings") as mock_settings:
        mock_settings.LEARN_LESSON_MIN_TARGETS = 2
        mock_settings.LEARN_LESSON_MAX_TARGETS = 7
        content, title, _ = content_and_meta_from_llm_payload(
            payload, skill_title="X"
        )
    assert len(content["targets"]) == 2
    assert title == "Morning coffee"
