from app.services.quiz_generation_service import (
    build_generation_prompt,
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
