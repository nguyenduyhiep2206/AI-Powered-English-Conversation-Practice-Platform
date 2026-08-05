from app.services.unit_enrichment_heuristic import run_heuristic

CATALOG = [
    {"slug": "modals_should_must", "title": "Should / must (advice/obligation)"},
    {"slug": "present_simple", "title": "Present simple"},
]


def test_language_focus_heading_yields_strong_cue():
    excerpt = "Language focus\nPractice should and must for advice.\n"
    r = run_heuristic(excerpt, unit_title="Unit 8 Fit and healthy", catalog_skills=CATALOG)
    assert r.strong is True
    assert "modals_should_must" in r.grammar_cues
    assert r.language_focus is not None
    assert "should" in r.language_focus.lower()


def test_thematic_title_alone_is_weak_without_body_cues():
    r = run_heuristic(
        "Some reading about people in a town.",
        unit_title="Unit 1 People",
        catalog_skills=CATALOG,
    )
    assert r.strong is False
    assert "present_simple" not in r.grammar_cues


def test_present_simple_slug_in_cues_when_tokens_in_excerpt():
    excerpt = "Grammar\nWe use the present simple for routines.\n"
    r = run_heuristic(excerpt, unit_title="Unit 2 Daily life", catalog_skills=CATALOG)
    assert r.strong is True
    assert "present_simple" in r.grammar_cues


def test_vocab_cues_from_unit_title_stopwords_filtered():
    r = run_heuristic(
        "Some reading text.",
        unit_title="Unit 3 Food and drink",
        catalog_skills=CATALOG,
    )
    assert "food" in r.vocab_cues
    assert "drink" in r.vocab_cues
    assert "unit" not in r.vocab_cues


def test_empty_excerpt_is_weak():
    r = run_heuristic("", unit_title="Unit 1 People", catalog_skills=CATALOG)
    assert r.strong is False
    assert r.language_focus is None
    assert r.grammar_cues == []


def test_single_common_token_does_not_yield_grammar_cue():
    """Loose single-token hits (much/have/so) must not mark catalog cues."""
    catalog = [
        {"slug": "quantifiers_much_many", "title": "Quantifiers much/many/a lot of"},
        {"slug": "modals_have_to", "title": "Have to / don't have to"},
        {"slug": "connectors_because_so", "title": "Connectors because/so/but"},
        {"slug": "first_conditional", "title": "First conditional"},
    ]
    excerpt = (
        "I’d like to stay in the UK for another month and improve my English. "
        "We have a break so that students can rest. There is much to do."
    )
    r = run_heuristic(excerpt, unit_title="Unit 2 Work and study", catalog_skills=catalog)
    assert r.grammar_cues == []
    assert r.strong is False


def test_dirty_language_focus_body_text_is_cleared_and_weak():
    excerpt = (
        "Language focus\n"
        "my city. I’d like to stay in the UK for another month and a "
        "Correct the spelling of the marked words. improve my English. "
        "1 What’s your home adress, please?\n"
    )
    r = run_heuristic(excerpt, unit_title="Unit 2 Work and study", catalog_skills=CATALOG)
    assert r.language_focus is None
    assert r.strong is False


def test_multi_token_skill_still_matches_phrase():
    catalog = [
        {"slug": "quantifiers_much_many", "title": "Quantifiers much/many/a lot of"},
    ]
    excerpt = "Language focus\nUse much and many with countable nouns.\n"
    r = run_heuristic(excerpt, unit_title="Unit 4 Food", catalog_skills=catalog)
    assert "quantifiers_much_many" in r.grammar_cues
    assert r.strong is True
    assert r.language_focus is not None
    assert "much" in r.language_focus.lower()
