from app.services.unit_enrichment_excerpt import (
    join_chunk_texts,
    truncate_excerpt,
    window_prefer_language_focus,
)


def test_join_chunk_texts_orders_by_chunk_index():
    chunks = [
        {"chunk_index": 1, "text": "second"},
        {"chunk_index": 0, "text": "first"},
    ]
    assert join_chunk_texts(chunks) == "first\n\nsecond"


def test_window_prefers_language_focus_heading():
    raw = "Intro fluff\n\nLanguage focus\nshould / must\nmore text"
    out = window_prefer_language_focus(raw)
    assert "Language focus" in out
    assert out.index("Language focus") == 0 or out.lstrip().startswith("Language focus")


def test_truncate_excerpt_respects_max():
    assert len(truncate_excerpt("a" * 5000, 3000)) == 3000


def test_window_ignores_mid_sentence_grammar():
    """Chunk breaks must not treat 'grammar and learn…' as a Grammar heading."""
    raw = (
        "I also want to improve my\n"
        "grammar and learn more vocabulary to help tourists in\n"
        "my city. I’d like to stay in the UK.\n\n"
        "Language focus\n"
        "quantifiers much / many\n"
    )
    out = window_prefer_language_focus(raw)
    assert out.lstrip().startswith("Language focus")
    assert "help tourists" not in out.split("Language focus")[0]
