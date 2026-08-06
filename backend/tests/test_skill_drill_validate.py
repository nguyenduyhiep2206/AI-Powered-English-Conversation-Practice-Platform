"""Unit tests for skill_drill LLM payload validation (validate_skill_drill_questions)."""

from app.services.quiz_generation_service import validate_skill_drill_questions


def _validate(items, blueprint):
    return validate_skill_drill_questions(
        items,
        blueprint=blueprint,
        surfaces={"am", "is", "because"},
        alignment="lesson",
    )


def test_accepts_sentence_build():
    bp = [{"item_kind": "sentence_build", "question_type": "sentence_build"}]
    items = [
        {
            "type": "sentence_build",
            "item_kind": "sentence_build",
            "stem": "Build a correct sentence with am.",
            "options": ["I", "am", "happy"],
            "answer": "I am happy",
        }
    ]
    out = _validate(items, bp)
    assert len(out) == 1
    assert out[0]["type"] == "sentence_build"
    assert out[0]["task_brief"]["mode"] == "skill_drill"
    assert out[0]["task_brief"]["item_kind"] == "sentence_build"


def test_rejects_sentence_build_token_not_in_options():
    bp = [{"item_kind": "sentence_build", "question_type": "sentence_build"}]
    items = [
        {
            "type": "sentence_build",
            "item_kind": "sentence_build",
            "stem": "Build a sentence.",
            "options": ["I", "am", "happy"],
            "answer": "I am student",
        }
    ]
    assert _validate(items, bp) == []


def test_rejects_sentence_build_too_few_tokens():
    bp = [{"item_kind": "sentence_build", "question_type": "sentence_build"}]
    items = [
        {
            "type": "sentence_build",
            "item_kind": "sentence_build",
            "stem": "Build.",
            "options": ["I", "am"],
            "answer": "I am",
        }
    ]
    assert _validate(items, bp) == []


def test_accepts_matching_and_canonicalizes_answer():
    bp = [{"item_kind": "matching", "question_type": "matching"}]
    items = [
        {
            "type": "matching",
            "item_kind": "matching",
            "stem": "Match connectors because and so.",
            "options": ["because|reason", "so|result", "but|contrast"],
            "answer": "so=>result;because=>reason;but=>contrast",
        }
    ]
    out = _validate(items, bp)
    assert len(out) == 1
    assert out[0]["answer"] == "because=>reason;but=>contrast;so=>result"
    assert out[0]["task_brief"]["pairs"] == [
        {"left": "because", "right": "reason"},
        {"left": "so", "right": "result"},
        {"left": "but", "right": "contrast"},
    ]


def test_rejects_matching_bad_pair_format():
    bp = [{"item_kind": "matching", "question_type": "matching"}]
    items = [
        {
            "type": "matching",
            "item_kind": "matching",
            "stem": "Match.",
            "options": ["because-reason", "so-result"],
            "answer": "because=>reason;so=>result",
        }
    ]
    assert _validate(items, bp) == []


def test_rejects_matching_answer_mismatch():
    bp = [{"item_kind": "matching", "question_type": "matching"}]
    items = [
        {
            "type": "matching",
            "item_kind": "matching",
            "stem": "Match.",
            "options": ["because|reason", "so|result"],
            "answer": "because=>wrong;so=>result",
        }
    ]
    assert _validate(items, bp) == []


def test_accepts_multi_select():
    bp = [{"item_kind": "multi_select", "question_type": "multi_select"}]
    items = [
        {
            "type": "multi_select",
            "item_kind": "multi_select",
            "stem": "Pick connectors because and so.",
            "options": ["because", "happy", "so", "apple"],
            "answer": "so | because",
        }
    ]
    out = _validate(items, bp)
    assert len(out) == 1
    assert out[0]["answer"] == "because | so"


def test_rejects_multi_select_only_one_correct():
    bp = [{"item_kind": "multi_select", "question_type": "multi_select"}]
    items = [
        {
            "type": "multi_select",
            "item_kind": "multi_select",
            "stem": "Pick one.",
            "options": ["because", "happy", "so"],
            "answer": "because",
        }
    ]
    assert _validate(items, bp) == []


def test_accepts_spot_error_mcq():
    bp = [{"item_kind": "spot_error", "question_type": "mcq"}]
    items = [
        {
            "type": "mcq",
            "item_kind": "spot_error",
            "stem": "My father work in an office, but today he is staying at home.",
            "options": ["work", "in an office", "is staying", "at home"],
            "answer": "work",
            "explanation": "Error: work / Correct: works / Why: 3rd person -s.",
        }
    ]
    out = _validate(items, bp)
    assert len(out) == 1
    assert out[0]["type"] == "mcq"
    assert out[0]["task_brief"]["item_kind"] == "spot_error"


def test_rejects_spot_error_valid_habit_vs_now_contrast():
    bp = [{"item_kind": "spot_error", "question_type": "mcq"}]
    items = [
        {
            "type": "mcq",
            "item_kind": "spot_error",
            "stem": "My father works in an office, but today he is staying at home.",
            "options": ["works", "in an office", "is staying", "at home"],
            "answer": "works",
            "explanation": "Error: works / Correct: is working / Why: wrong.",
        }
    ]
    assert _validate(items, bp) == []


def test_rejects_spot_error_continuous_then_usually_habit():
    bp = [{"item_kind": "spot_error", "question_type": "mcq"}]
    items = [
        {
            "type": "mcq",
            "item_kind": "spot_error",
            "stem": "My sister is drinking coffee, but she usually works in the morning.",
            "options": ["is drinking", "coffee", "usually", "works"],
            "answer": "works",
            "explanation": (
                "Error: works / Correct: works / Why: The sentence is grammatically "
                "correct as written; however, 'works' is the correct present simple."
            ),
        }
    ]
    assert _validate(items, bp) == []


def test_rejects_spot_error_explanation_error_equals_correct():
    bp = [{"item_kind": "spot_error", "question_type": "mcq"}]
    items = [
        {
            "type": "mcq",
            "item_kind": "spot_error",
            "stem": "They is here with friends now.",
            "options": ["They", "is", "here", "now"],
            "answer": "is",
            "explanation": "Error: is / Correct: is / Why: same.",
        }
    ]
    assert _validate(items, bp) == []


def test_rejects_spot_error_option_missing_from_stem():
    bp = [{"item_kind": "spot_error", "question_type": "mcq"}]
    items = [
        {
            "type": "mcq",
            "item_kind": "spot_error",
            "stem": "They is here today.",
            "options": ["They", "is", "here", "are"],
            "answer": "is",
            "explanation": "Error: is / Correct: are / Why: plural subject.",
        }
    ]
    assert _validate(items, bp) == []


def test_accepts_dialogue_complete_mcq():
    bp = [{"item_kind": "dialogue_complete", "question_type": "mcq"}]
    items = [
        {
            "type": "mcq",
            "item_kind": "dialogue_complete",
            "stem": "A: How ___ you?\nB: I am fine.",
            "options": ["is", "are", "am"],
            "answer": "are",
        }
    ]
    out = _validate(items, bp)
    assert len(out) == 1
    assert out[0]["task_brief"]["item_kind"] == "dialogue_complete"


def test_rejects_kind_type_mismatch():
    bp = [{"item_kind": "sentence_build", "question_type": "sentence_build"}]
    items = [
        {
            "type": "mcq",
            "item_kind": "spot_error",
            "stem": "Wrong kind.",
            "options": ["a", "b"],
            "answer": "a",
        }
    ]
    assert _validate(items, bp) == []


def test_rejects_wrong_type_for_kind():
    bp = [{"item_kind": "spot_error", "question_type": "mcq"}]
    items = [
        {
            "type": "sentence_build",
            "item_kind": "spot_error",
            "stem": "Build.",
            "options": ["I", "am", "happy"],
            "answer": "I am happy",
        }
    ]
    assert _validate(items, bp) == []


def test_grammar_blueprint_batch():
    from app.services.skill_drill_blueprint import blueprint_for_skill_drill

    bp = blueprint_for_skill_drill("grammar", 6)
    items = [
        {
            "type": "mcq",
            "item_kind": "form_choose",
            "stem": "She ___ happy.",
            "options": ["am", "is", "are", "be"],
            "answer": "is",
        },
        {
            "type": "cloze",
            "item_kind": "cloze_form",
            "stem": "I ___(be) a student.",
            "options": [],
            "answer": "am",
        },
        {
            "type": "fix_grammar",
            "item_kind": "fix_grammar",
            "stem": "She are happy.",
            "options": [],
            "answer": "She is happy.",
        },
        {
            "type": "mcq",
            "item_kind": "spot_error",
            "stem": "They is here with am now.",
            "options": ["They", "is", "here", "now"],
            "answer": "is",
            "explanation": "Error: is / Correct: are / Why: plural they.",
        },
        {
            "type": "sentence_build",
            "item_kind": "sentence_build",
            "stem": "Build with am.",
            "options": ["I", "am", "happy"],
            "answer": "I am happy",
        },
        {
            "type": "mcq",
            "item_kind": "contrast",
            "stem": "I ___ tired.",
            "options": ["am", "is", "are", "be"],
            "answer": "am",
        },
    ]
    out = _validate(items, bp)
    assert len(out) == 6
    assert [row["task_brief"]["item_kind"] for row in out] == [
        b["item_kind"] for b in bp
    ]
