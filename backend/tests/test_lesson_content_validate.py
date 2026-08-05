from app.services.lesson_content_validate import (
    MAX_CHECKS,
    MIN_CHECKS,
    assert_publishable,
    normalize_content,
    target_bounds,
)


def test_normalize_valid_content():
    content = normalize_content(
        {
            "passage": {
                "text": "Mai gets up at six every day and goes to work.",
                "gloss": "A morning routine.",
            },
            "targets": [
                {"surface": "gets up", "gloss": "wakes up and leaves bed"},
                {"surface": "at six", "gloss": "at 6 o'clock"},
                {"surface": "goes to work", "gloss": "travels to her job"},
                {"surface": "every day", "gloss": "each day"},
            ],
            "checks": [
                {
                    "type": "mcq",
                    "prompt": "What does gets up mean?",
                    "options": ["wakes up and leaves bed", "goes to sleep", "eats breakfast"],
                    "answer": "wakes up and leaves bed",
                }
            ],
            "writing": {
                "prompt": "Write two sentences about your morning routine.",
                "min_words": 10,
            },
        }
    )
    min_t, max_t = target_bounds()
    assert content["passage"]["text"].startswith("Mai")
    assert content["targets"][0]["gloss"].startswith("wakes")
    assert min_t <= len(content["targets"]) <= max_t
    assert MIN_CHECKS <= len(content["checks"]) <= MAX_CHECKS
    assert content["writing"]["must_use"]


def test_accepts_legacy_gloss_vi_key():
    content = normalize_content(
        {
            "passage": {"text": "She drinks coffee every morning before work."},
            "targets": [
                {"surface": "drinks", "gloss_vi": "takes a drink of"},
                {"surface": "coffee", "gloss_en": "a hot brown drink"},
                {"surface": "every morning", "gloss": "each morning"},
                {"surface": "before work", "gloss": "earlier than work time"},
            ],
            "checks": [
                {
                    "type": "mcq",
                    "prompt": "What is coffee?",
                    "options": ["a hot brown drink", "a car", "a book"],
                    "answer": "a hot brown drink",
                }
            ],
            "writing": {"prompt": "Write about your morning."},
        }
    )
    assert content["targets"][0]["gloss"] == "takes a drink of"
    assert content["targets"][1]["gloss"] == "a hot brown drink"


def test_reject_too_few_targets():
    try:
        normalize_content(
            {
                "passage": {"text": "Hello."},
                "targets": [{"surface": "a"}, {"surface": "b"}],
                "checks": [
                    {
                        "type": "mcq",
                        "prompt": "p",
                        "options": ["a", "b"],
                        "answer": "a",
                    }
                ],
                "writing": {"prompt": "Write."},
            }
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "targets" in str(exc)


def test_drops_orphan_targets_when_enough_remain():
    content = normalize_content(
        {
            "passage": {
                "text": (
                    "I have a pen and a bag. I eat an apple. "
                    "I am a student today."
                )
            },
            "targets": [
                {"surface": "a pen", "gloss": "one pen"},
                {"surface": "a bag", "gloss": "one bag"},
                {"surface": "an apple", "gloss": "one apple"},
                {"surface": "a student", "gloss": "one student"},
                {"surface": "a person", "gloss": "one person"},  # not in passage
            ],
            "checks": [
                {
                    "type": "mcq",
                    "prompt": "Which comes after an?",
                    "options": ["apple", "pen", "bag"],
                    "answer": "apple",
                }
            ],
            "writing": {
                "prompt": "Write about your bag.",
                "must_use": ["a pen", "a person"],
            },
        }
    )
    surfaces = {t["surface"] for t in content["targets"]}
    assert "a person" not in surfaces
    assert "a pen" in surfaces
    assert "a person" not in content["writing"]["must_use"]
    assert len(content["targets"]) >= 4


def test_reject_too_few_targets_after_orphan_drop():
    try:
        normalize_content(
            {
                "passage": {"text": "I have a pen only."},
                "targets": [
                    {"surface": "a pen"},
                    {"surface": "a bag"},
                    {"surface": "an apple"},
                    {"surface": "a student"},
                ],
                "checks": [
                    {
                        "type": "mcq",
                        "prompt": "p",
                        "options": ["a", "b"],
                        "answer": "a",
                    }
                ],
                "writing": {"prompt": "Write."},
            }
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "targets" in str(exc)
        assert "dropped" in str(exc) or "passage" in str(exc)
    assert_publishable(
        {
            "passage": {"text": "She drinks coffee every morning before work."},
            "targets": [
                {"surface": "drinks"},
                {"surface": "coffee"},
                {"surface": "every morning"},
                {"surface": "before work"},
            ],
            "checks": [
                {
                    "type": "cloze",
                    "prompt": "She ___ coffee.",
                    "options": [],
                    "answer": "drinks",
                }
            ],
            "writing": {"prompt": "Write about your morning.", "must_use": ["drinks"]},
        }
    )


def test_normalize_keeps_form_rows():
    raw = {
        "passage": {"text": "I am happy. She is kind. They are friends."},
        "form": {
            "title": "Verb to be",
            "rows": [
                {"label": "I", "pattern": "am", "example": "I am happy."},
                {"label": "She", "pattern": "is", "example": "She is kind."},
            ],
        },
        "targets": [
            {"surface": "am", "gloss": "form of be for I"},
            {"surface": "is", "gloss": "form of be for he/she"},
            {"surface": "are", "gloss": "form of be for they"},
            {"surface": "happy", "gloss": "feeling good"},
        ],
        "checks": [
            {
                "type": "mcq",
                "prompt": "I ___ happy.",
                "options": ["am", "is", "are"],
                "answer": "am",
            }
        ],
        "writing": {"prompt": "Write two sentences with am/is."},
    }
    out = normalize_content(raw)
    assert out["form"]["rows"][0]["pattern"] == "am"


def test_assert_publishable_grammar_requires_form():
    import pytest

    raw = {
        "passage": {"text": "I am happy. She is kind. They are friends here."},
        "targets": [
            {"surface": "am", "gloss": "be for I"},
            {"surface": "is", "gloss": "be for she"},
            {"surface": "are", "gloss": "be for they"},
            {"surface": "happy", "gloss": "glad"},
        ],
        "checks": [
            {
                "type": "mcq",
                "prompt": "I ___ happy.",
                "options": ["am", "is", "are"],
                "answer": "am",
            }
        ],
        "writing": {"prompt": "Write two sentences with am/is."},
    }
    content = normalize_content(raw)
    with pytest.raises(ValueError, match="form"):
        assert_publishable(content, skill_type="grammar")


def test_assert_publishable_grammar_form_optional_when_disabled():
    raw = {
        "passage": {"text": "I am happy. She is kind. They are friends here."},
        "targets": [
            {"surface": "am", "gloss": "be for I"},
            {"surface": "is", "gloss": "be for she"},
            {"surface": "are", "gloss": "be for they"},
            {"surface": "happy", "gloss": "glad"},
        ],
        "checks": [
            {
                "type": "mcq",
                "prompt": "I ___ happy.",
                "options": ["am", "is", "are"],
                "answer": "am",
            }
        ],
        "writing": {"prompt": "Write two sentences with am/is."},
    }
    content = normalize_content(raw)
    assert_publishable(
        content, skill_type="grammar", require_grammar_form=False
    )


def test_target_match_tolerates_curly_apostrophe():
    from app.services.lesson_content_validate import fold_text

    passage = "Canada’s oldest company is here."  # U+2019
    surface = "Canada's oldest company"  # ASCII '
    assert fold_text(surface) in fold_text(passage)

    out = normalize_content(
        {
            "passage": {"text": passage + " I am glad. She is kind. They are fine."},
            "targets": [
                {"surface": "Canada's oldest company", "gloss": "phrase"},
                {"surface": "am", "gloss": "be"},
                {"surface": "is", "gloss": "be"},
                {"surface": "are", "gloss": "be"},
            ],
            "checks": [
                {
                    "type": "mcq",
                    "prompt": "I ___ glad.",
                    "options": ["am", "is", "are"],
                    "answer": "am",
                }
            ],
            "writing": {"prompt": "Write."},
        }
    )
    assert out["targets"][0]["surface"] == "Canada's oldest company"
