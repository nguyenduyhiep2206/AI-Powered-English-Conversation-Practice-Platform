from app.models.enums import CEFRLevel
from app.services.quiz_generation_service import (
    build_generation_prompt,
    passage_grounded,
    passage_length_ok,
    validate_generated_questions,
)


def test_validate_mcq_hop_le():
    raw = [
        {
            "type": "mcq",
            "stem": "Choose the correct form: I ___ here since 2020.",
            "options": ["lived", "have lived", "live", "am living"],
            "answer": "have lived",
            "explanation": "Present perfect with since.",
            "skill": "grammar",
            "difficulty": "medium",
        }
    ]
    ok = validate_generated_questions(raw)
    assert len(ok) == 1
    assert ok[0]["answer"] == "have lived"
    assert ok[0].get("passage") is None


def test_validate_mcq_thieu_option_bi_loai():
    raw = [{"type": "mcq", "stem": "x", "options": ["a"], "answer": "a", "skill": "grammar"}]
    assert validate_generated_questions(raw) == []


def test_validate_mcq_answer_khong_nam_trong_options():
    raw = [
        {
            "type": "mcq",
            "stem": "x",
            "options": ["a", "b", "c", "d"],
            "answer": "z",
            "skill": "grammar",
        }
    ]
    assert validate_generated_questions(raw) == []


def test_prompt_co_ten_unit_va_so_cau():
    prompt = build_generation_prompt(
        unit_title="Present perfect 1 (I have done)",
        cefr_level="B1",
        context="We use the present perfect...",
        count=5,
    )
    assert "Present perfect 1" in prompt
    assert "5" in prompt
    assert "We use the present perfect" in prompt


def test_prompt_includes_can_do_and_blueprint():
    from app.services.cefr_descriptors import blueprint_for
    from app.models.enums import BookTypeEnum, SkillTypeEnum

    bp = blueprint_for(BookTypeEnum.reading_practice, SkillTypeEnum.reading, 3)
    prompt = build_generation_prompt(
        unit_title="Max the Cat",
        cefr_level="A2",
        context="Max the cat sat on the mat.",
        count=3,
        can_do="CEFR A2 reading: understand short simple texts",
        blueprint=bp,
        skill_type="reading",
        book_type="reading_practice",
    )
    assert "Can-do target:" in prompt
    assert "Item blueprint" in prompt
    assert "requires_passage=True" in prompt
    assert "reading_practice" in prompt


def test_context_budget_and_mode():
    from app.services.quiz_generation_service import context_budget_for_level, context_mode_for
    from app.models.enums import BookTypeEnum, CEFRLevel, SkillTypeEnum

    assert context_budget_for_level(CEFRLevel.C1) >= context_budget_for_level(CEFRLevel.A1)
    assert context_budget_for_level(CEFRLevel.C1) <= 8000
    assert context_mode_for(BookTypeEnum.reading_practice, SkillTypeEnum.grammar) == "stride"
    assert context_mode_for(BookTypeEnum.grammar_textbook, SkillTypeEnum.grammar) == "prefix"


def test_passage_grounded_substring():
    excerpt = "The old man waits at the post office every morning."
    assert passage_grounded("old man waits at the post office", excerpt) is True
    assert passage_grounded("completely unrelated fantasy text here", excerpt) is False


def test_passage_length_ok_rejects_extreme():
    assert passage_length_ok("x" * 200, CEFRLevel.B1) is True
    assert passage_length_ok("short", CEFRLevel.B1) is False  # < 250/2
    assert passage_length_ok("x" * 5000, CEFRLevel.B1) is False  # > 700*2


def test_validate_requires_passage_when_blueprint_says_so():
    excerpt = (
        "Max the cat sat on the mat and watched the birds outside the window. "
        "He wanted to catch one but the glass stopped him."
    )
    blueprint = [{"type": "mcq", "requires_passage": True, "cefr_focus": "detail"}]
    missing = [
        {
            "type": "mcq",
            "stem": "Where did Max sit?",
            "options": ["mat", "roof", "car", "box"],
            "answer": "mat",
        }
    ]
    assert (
        validate_generated_questions(
            missing, excerpt=excerpt, blueprint=blueprint, cefr_level=CEFRLevel.A2
        )
        == []
    )

    grounded = [
        {
            "type": "mcq",
            "passage": "Max the cat sat on the mat and watched the birds outside the window.",
            "stem": "Where did Max sit?",
            "options": ["mat", "roof", "car", "box"],
            "answer": "mat",
            "difficulty": "easy",
        }
    ]
    ok = validate_generated_questions(
        grounded, excerpt=excerpt, blueprint=blueprint, cefr_level=CEFRLevel.A2
    )
    assert len(ok) == 1
    assert "Max the cat" in (ok[0]["passage"] or "")


def test_validate_rejects_ungrounded_passage():
    excerpt = "We use the present perfect with since and for."
    blueprint = [{"type": "mcq", "requires_passage": True, "cefr_focus": "grammar_in_context"}]
    raw = [
        {
            "type": "mcq",
            "passage": "Once upon a time in a galaxy far away the robots danced.",
            "stem": "Choose the tense.",
            "options": ["a", "b", "c", "d"],
            "answer": "a",
        }
    ]
    assert (
        validate_generated_questions(
            raw, excerpt=excerpt, blueprint=blueprint, cefr_level=CEFRLevel.B1
        )
        == []
    )


def test_validate_rejects_passage_length_way_off_level():
    excerpt = "word " * 400
    blueprint = [{"type": "mcq", "requires_passage": True, "cefr_focus": "detail"}]
    # Tiny passage for B1 band (min 250 → reject < 125)
    raw = [
        {
            "type": "mcq",
            "passage": "word word word",
            "stem": "What repeats?",
            "options": ["word", "cat", "dog", "bird"],
            "answer": "word",
        }
    ]
    assert (
        validate_generated_questions(
            raw, excerpt=excerpt, blueprint=blueprint, cefr_level=CEFRLevel.B1
        )
        == []
    )
