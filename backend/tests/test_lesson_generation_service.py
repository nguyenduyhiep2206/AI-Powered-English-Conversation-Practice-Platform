from app.services.lesson_generation_service import _build_system_prompt
from app.services.lesson_content_validate import normalize_content


def test_system_prompt_includes_skill_guidance_and_cefr():
    grammar = _build_system_prompt(skill_type="grammar", cefr="A2")
    assert "grammar" in grammar.lower()
    assert "A2" in grammar
    assert "Vietnamese" in grammar or "English→English" in grammar or "English only" in grammar
    reading = _build_system_prompt(skill_type="reading", cefr="B1")
    assert "passage" in reading.lower()
    assert "B1" in reading


def test_normalize_llm_shaped_payload():
    content = normalize_content(
        {
            "passage": {"text": "Tom drinks coffee every morning before work."},
            "targets": [
                {"surface": "drinks", "gloss": "takes a drink of"},
                {"surface": "coffee", "gloss": "a hot brown drink"},
                {"surface": "every morning", "gloss": "each morning"},
                {"surface": "before work", "gloss": "earlier than work time"},
                {"surface": "Tom", "gloss": "a man's name"},
            ],
            "checks": [
                {
                    "type": "mcq",
                    "prompt": "What does drinks mean here?",
                    "options": ["takes a drink of", "eats", "sleeps"],
                    "answer": "takes a drink of",
                },
                {
                    "type": "cloze",
                    "prompt": "Tom ___ coffee.",
                    "options": [],
                    "answer": "drinks",
                },
            ],
            "writing": {
                "prompt": "Write two sentences about your morning.",
                "min_words": 12,
                "must_use": ["drinks", "every morning"],
            },
        }
    )
    assert len(content["targets"]) == 5
    assert len(content["checks"]) == 2
    assert content["targets"][0]["gloss"] == "takes a drink of"
