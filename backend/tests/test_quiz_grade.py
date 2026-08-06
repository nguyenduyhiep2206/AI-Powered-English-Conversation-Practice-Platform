from app.services.quiz_grade import (
    canonicalize_fix_grammar,
    canonicalize_matching_answer,
    canonicalize_multi_select,
    canonicalize_sentence_build,
    grade_answer,
    normalize_space_lower,
)


def test_normalize_space_lower():
    assert normalize_space_lower("  Hello   World  ") == "hello world"


def test_grade_mcq_parity():
    assert grade_answer("mcq", "Have lived", "have lived") is True
    assert grade_answer("mcq", "have lived", "lived") is False
    assert grade_answer("cloze", "answer", "ANSWER") is True
    assert grade_answer("fix_grammar", "She goes", "she goes") is True


def test_fix_grammar_ignores_clause_punctuation():
    expected = "He is not playing tennis at the moment; he is playing football."
    with_comma = "He is not playing tennis at the moment, he is playing football."
    with_period = "He is not playing tennis at the moment. He is playing football."
    assert canonicalize_fix_grammar(expected) == canonicalize_fix_grammar(
        with_comma
    )
    assert grade_answer("fix_grammar", expected, with_comma) is True
    assert grade_answer("fix_grammar", expected, with_period) is True
    assert (
        grade_answer(
            "fix_grammar",
            expected,
            "He is not playing tennis at the moment, he plays football.",
        )
        is False
    )


def test_canonicalize_sentence_build():
    assert canonicalize_sentence_build("  I   have   lived ") == "i have lived"


def test_grade_sentence_build():
    assert grade_answer("sentence_build", "I have lived", "i  have lived") is True
    assert grade_answer("sentence_build", "I have lived", "i have") is False


def test_canonicalize_multi_select():
    assert canonicalize_multi_select("A | B") == {"a", "b"}
    assert canonicalize_multi_select("a;b") == {"a", "b"}
    assert canonicalize_multi_select("  Foo  |  Bar  ") == {"foo", "bar"}


def test_grade_multi_select_order_insensitive():
    assert grade_answer("multi_select", "a | b", "b | a") is True
    assert grade_answer("multi_select", "a | b", "a | c") is False
    assert grade_answer("multi_select", "A;B", "b | a") is True


def test_canonicalize_matching():
    assert canonicalize_matching_answer("b=>y;a=>x") == "a=>x;b=>y"
    assert canonicalize_matching_answer("a|x") == "a=>x"
    assert canonicalize_matching_answer("b|y;a|x") == "a=>x;b=>y"


def test_grade_matching():
    assert grade_answer("matching", "a=>x;b=>y", "b=>y;a=>x") is True
    assert grade_answer("matching", "a=>x;b=>y", "a|x;b|y") is True
    assert grade_answer("matching", "a=>x;b=>y", "a=>x;b=>z") is False
