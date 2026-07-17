"""CEFR can-do descriptors, passage length hints, and quiz item blueprints."""

from __future__ import annotations

from typing import Any, TypedDict

from app.models.enums import BookTypeEnum, CEFRLevel, SkillTypeEnum


class BlueprintItem(TypedDict):
    type: str
    requires_passage: bool
    cefr_focus: str


# --- Can-do (short EN descriptors for prompt injection) ---

_READING_CAN_DO: dict[CEFRLevel, str] = {
    CEFRLevel.A1: (
        "CEFR A1 reading: understand very short, simple notices and familiar everyday "
        "sentences; questions target explicit wording only."
    ),
    CEFRLevel.A2: (
        "CEFR A2 reading: understand short simple texts on everyday topics; "
        "questions target clear facts stated in the passage."
    ),
    CEFRLevel.B1: (
        "CEFR B1 reading: understand the main points of straightforward factual or "
        "narrative passages; questions may ask main idea or clearly stated detail."
    ),
    CEFRLevel.B2: (
        "CEFR B2 reading: understand articles and viewpoints in moderately complex "
        "passages; questions may require paraphrase or simple inference."
    ),
    CEFRLevel.C1: (
        "CEFR C1 reading: understand longer demanding texts, including implied meaning "
        "and tone; questions may target nuance, attitude, or careful inference."
    ),
}

_GRAMMAR_CAN_DO: dict[CEFRLevel, str] = {
    CEFRLevel.A1: (
        "CEFR A1 grammar-in-context: recognise basic forms (be, present simple) "
        "inside given sentences from the book."
    ),
    CEFRLevel.A2: (
        "CEFR A2 grammar-in-context: common tenses and high-frequency patterns "
        "as used in short book sentences."
    ),
    CEFRLevel.B1: (
        "CEFR B1 grammar-in-context: extended sentences and common connectors "
        "as they appear in the excerpt."
    ),
    CEFRLevel.B2: (
        "CEFR B2 grammar-in-context: more complex structures and paraphrase of "
        "meaning within the book exemplar."
    ),
    CEFRLevel.C1: (
        "CEFR C1 grammar-in-context: subtle structural or lexical choices "
        "grounded in the provided book sentences."
    ),
}

_VOCAB_CAN_DO: dict[CEFRLevel, str] = {
    CEFRLevel.A1: (
        "CEFR A1 vocab-in-context: concrete everyday words as used in the short passage."
    ),
    CEFRLevel.A2: (
        "CEFR A2 vocab-in-context: high-frequency words/phrases whose meaning is "
        "supported by the surrounding sentences."
    ),
    CEFRLevel.B1: (
        "CEFR B1 vocab-in-context: meaning of words/phrases from context in a clear passage."
    ),
    CEFRLevel.B2: (
        "CEFR B2 vocab-in-context: less common items or shades of meaning supported by the text."
    ),
    CEFRLevel.C1: (
        "CEFR C1 vocab-in-context: precise or nuanced vocabulary as evidenced in the passage."
    ),
}

_FUNCTIONAL_CAN_DO: dict[CEFRLevel, str] = {
    level: (
        f"CEFR {level.value} functional language-in-context: choose or complete "
        "appropriate expressions as shown in the book excerpt."
    )
    for level in CEFRLevel
}

_CAN_DO_BY_SKILL: dict[SkillTypeEnum, dict[CEFRLevel, str]] = {
    SkillTypeEnum.reading: _READING_CAN_DO,
    SkillTypeEnum.grammar: _GRAMMAR_CAN_DO,
    SkillTypeEnum.vocabulary: _VOCAB_CAN_DO,
    SkillTypeEnum.functional: _FUNCTIONAL_CAN_DO,
}

# --- Passage length (chars), from plan §1.1 ---

_PASSAGE_LENGTH: dict[CEFRLevel, tuple[int, int]] = {
    CEFRLevel.A1: (120, 400),
    CEFRLevel.A2: (120, 400),
    CEFRLevel.B1: (250, 700),
    CEFRLevel.B2: (400, 1200),
    CEFRLevel.C1: (400, 1200),
}

# Blueprint templates: (type, requires_passage, cefr_focus) repeating patterns
_READING_PATTERN: list[tuple[str, bool, str]] = [
    ("mcq", True, "main_idea"),
    ("mcq", True, "detail"),
    ("cloze", True, "cloze_in_passage"),
    ("mcq", True, "vocab_in_context"),
    ("mcq", True, "inference"),
    ("mcq", True, "detail"),
    ("cloze", True, "cloze_in_passage"),
    ("mcq", True, "vocab_in_context"),
]

_GRAMMAR_PATTERN: list[tuple[str, bool, str]] = [
    ("mcq", True, "grammar_in_context"),
    ("mcq", True, "grammar_in_context"),
    ("cloze", True, "cloze_in_passage"),
    ("fix_grammar", True, "fix_grammar"),
    ("mcq", True, "grammar_in_context"),
    ("mcq", True, "grammar_in_context"),
    ("cloze", True, "cloze_in_passage"),
    ("fix_grammar", True, "fix_grammar"),
]


def _normalize_level(level: CEFRLevel | str) -> CEFRLevel:
    if isinstance(level, CEFRLevel):
        return level
    return CEFRLevel(str(level))


def _normalize_skill(skill_type: SkillTypeEnum | str) -> SkillTypeEnum:
    if isinstance(skill_type, SkillTypeEnum):
        return skill_type
    return SkillTypeEnum(str(skill_type))


def _normalize_book_type(book_type: BookTypeEnum | str | None) -> BookTypeEnum | None:
    if book_type is None:
        return None
    if isinstance(book_type, BookTypeEnum):
        return book_type
    return BookTypeEnum(str(book_type))


def get_can_do(level: CEFRLevel | str, skill_type: SkillTypeEnum | str) -> str:
    """Return a short CEFR can-do string for prompt injection."""
    cefr = _normalize_level(level)
    skill = _normalize_skill(skill_type)
    table = _CAN_DO_BY_SKILL.get(skill, _GRAMMAR_CAN_DO)
    return table[cefr]


def passage_length_range(level: CEFRLevel | str) -> tuple[int, int]:
    """Return (min_chars, max_chars) suggested passage length for the level."""
    return _PASSAGE_LENGTH[_normalize_level(level)]


def _select_pattern(
    book_type: BookTypeEnum | None,
    skill_type: SkillTypeEnum,
) -> list[tuple[str, bool, str]]:
    if book_type == BookTypeEnum.reading_practice or skill_type == SkillTypeEnum.reading:
        return _READING_PATTERN
    return _GRAMMAR_PATTERN


def blueprint_for(
    book_type: BookTypeEnum | str | None,
    skill_type: SkillTypeEnum | str,
    count: int,
) -> list[BlueprintItem]:
    """
    Build a list of item specs for one generate batch.

    Each item: type (mcq|cloze|fix_grammar), requires_passage, cefr_focus.
    """
    if count < 1:
        raise ValueError("count must be >= 1")

    skill = _normalize_skill(skill_type)
    book = _normalize_book_type(book_type)
    pattern = _select_pattern(book, skill)

    items: list[BlueprintItem] = []
    for index in range(count):
        qtype, requires_passage, focus = pattern[index % len(pattern)]
        items.append(
            {
                "type": qtype,
                "requires_passage": requires_passage,
                "cefr_focus": focus,
            }
        )
    return items


def blueprint_as_prompt_lines(items: list[BlueprintItem] | list[dict[str, Any]]) -> str:
    """Human-readable blueprint block for the LLM user prompt."""
    lines = ["Item blueprint (follow order and focus):"]
    for i, item in enumerate(items, start=1):
        lines.append(
            f"{i}. type={item['type']}; requires_passage={item['requires_passage']}; "
            f"cefr_focus={item['cefr_focus']}"
        )
    return "\n".join(lines)
