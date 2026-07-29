from app.services.lesson_content_validate import (
    MAX_CHECKS,
    MAX_TARGETS,
    MIN_CHECKS,
    MIN_TARGETS,
    assert_publishable,
    normalize_content,
)


def test_normalize_valid_content():
    content = normalize_content(
        {
            "passage": {"text": "Mai gets up at six.", "gloss": "A morning routine."},
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
    assert content["passage"]["text"].startswith("Mai")
    assert content["targets"][0]["gloss"].startswith("wakes")
    assert MIN_TARGETS <= len(content["targets"]) <= MAX_TARGETS
    assert MIN_CHECKS <= len(content["checks"]) <= MAX_CHECKS
    assert content["writing"]["must_use"]


def test_accepts_legacy_gloss_vi_key():
    content = normalize_content(
        {
            "passage": {"text": "She drinks coffee."},
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


def test_assert_publishable_ok():
    assert_publishable(
        {
            "passage": {"text": "She drinks coffee."},
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
