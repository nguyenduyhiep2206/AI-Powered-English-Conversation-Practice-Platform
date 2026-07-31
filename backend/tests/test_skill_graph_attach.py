import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import BookStatusEnum, CEFRLevel
from app.services import skill_graph_service as sgs
from app.services.skill_graph_llm_service import attach_units_with_llm
from app.services.skill_graph_service import _unit_dicts, build_rule_attach_mappings
from app.services.skill_graph_validate import validate_llm_attach_payload


def test_validate_attach_rejects_unknown_slug():
    with pytest.raises(ValueError, match="not in the catalog"):
        validate_llm_attach_payload(
            {
                "unit_mappings": [
                    {"unit_index": 1, "slug": "not_in_catalog", "exclude": False},
                ]
            },
            unit_indexes={1},
            catalog_slugs={"present_simple"},
        )


def test_validate_attach_allows_null_slug_unmapped():
    out = validate_llm_attach_payload(
        {
            "unit_mappings": [
                {"unit_index": 1, "slug": None, "exclude": False},
                {"unit_index": 2, "slug": "present_simple", "exclude": False},
            ]
        },
        unit_indexes={1, 2},
        catalog_slugs={"present_simple"},
    )
    assert out[0]["slug"] is None
    assert out[1]["slug"] == "present_simple"


def test_rule_attach_mapping_only_catalog():
    catalog = {"present_simple", "past_simple_regular"}
    units = [
        {"unit_index": 1, "title": "Present simple"},
        {"unit_index": 2, "title": "Totally Unique Chapter About Dragons"},
        {"unit_index": 3, "title": "Review Unit 1-3"},
    ]
    mappings = build_rule_attach_mappings(units, catalog_slugs=catalog)
    by_i = {m["unit_index"]: m for m in mappings}
    assert by_i[1]["slug"] == "present_simple"
    assert by_i[2]["slug"] is None
    assert by_i[3]["exclude"] is True


def test_rule_attach_uses_grammar_cue_when_title_unmapped():
    units = [
        {
            "unit_index": 0,
            "title": "Unit 8 Fit and healthy",
            "grammar_cues": ["modals_should_must"],
        }
    ]
    mappings = build_rule_attach_mappings(
        units, catalog_slugs={"modals_should_must", "present_simple"}
    )
    assert mappings[0]["slug"] == "modals_should_must"
    assert mappings[0]["exclude"] is False


def test_llm_attach_input_units_include_cues_not_excerpt():
    units = [
        {
            "unit_index": 0,
            "title": "Unit 8 Fit and healthy",
            "language_focus": "should and must",
            "grammar_cues": ["modals_should_must"],
            "vocab_cues": ["healthy"],
            "content_summary": "Giving advice",
            "excerpt": "raw page text must not be sent",
            "text": "also forbidden",
        }
    ]
    out = sgs._llm_attach_input_units(units)
    unit = out[0]
    assert "excerpt" not in unit and "text" not in unit
    assert unit["grammar_cues"] == ["modals_should_must"]
    assert unit["language_focus"] == "should and must"
    assert unit["vocab_cues"] == ["healthy"]
    assert unit["content_summary"] == "Giving advice"
    assert unit["title"] == "Unit 8 Fit and healthy"


def test_attach_units_with_llm_happy_path():
    fake = {
        "unit_mappings": [
            {"unit_index": 0, "slug": "be_present", "exclude": False},
        ]
    }
    catalog = [{"slug": "be_present", "title": "Be", "difficulty_in_level": 1}]
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=fake):
        mappings = attach_units_with_llm(
            cefr_level="A1",
            book_title="Book",
            catalog_skills=catalog,
            units=[{"unit_index": 0, "title": "Hello", "rule_slug": "hello"}],
        )
    assert mappings[0]["slug"] == "be_present"


def test_attach_units_with_llm_rejects_non_object():
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=[]):
        with pytest.raises(ValueError, match="must be an object"):
            attach_units_with_llm(
                cefr_level="A1",
                book_title="Book",
                catalog_skills=[{"slug": "be_present", "title": "Be"}],
                units=[{"unit_index": 0, "title": "Hello", "rule_slug": "hello"}],
            )


def test_unit_dicts_includes_enrich_signals():
    unit = MagicMock()
    unit.id = 10
    unit.title = "Unit 1"
    unit.unit_index = 0
    unit.depth_or_source = "toc"
    unit.language_focus = "present simple"
    unit.grammar_cues = ["present simple"]
    unit.vocab_cues = ["people"]
    unit.content_summary = "Introducing yourself"
    out = _unit_dicts([unit])
    assert out[0]["language_focus"] == "present simple"
    assert out[0]["grammar_cues"] == ["present simple"]
    assert out[0]["vocab_cues"] == ["people"]
    assert out[0]["content_summary"] == "Introducing yourself"


def test_sync_skills_invokes_enrich_when_enabled():
    book = MagicMock()
    book.id = 48
    book.title = "Empower"
    book.status = BookStatusEnum.ready
    book.cefr_level = CEFRLevel.A2
    book.book_type = None

    unit = MagicMock()
    unit.id = 1
    unit.title = "Present simple"
    unit.unit_index = 0
    unit.depth_or_source = "toc"
    unit.language_focus = None
    unit.grammar_cues = None
    unit.vocab_cues = None
    unit.content_summary = None

    enrich_meta = {
        "enriched": 1,
        "method_counts": {"heuristic": 1, "heuristic+llm": 0, "skipped": 0},
        "source_counts": {"chunks": 1, "pdf_skim": 0},
    }
    catalog = [
        {
            "id": 99,
            "slug": "present_simple",
            "title": "Present simple",
            "difficulty_in_level": 1,
        }
    ]
    enrich = AsyncMock(return_value=enrich_meta)
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    async def run():
        with (
            patch.object(sgs.settings, "UNIT_ENRICH_ENABLED", True),
            patch.object(
                sgs, "_load_ready_book_and_units", AsyncMock(return_value=(book, [unit]))
            ),
            patch(
                "app.services.unit_enrichment_service.enrich_units_for_book",
                enrich,
            ),
            patch.object(sgs, "load_catalog_skills", AsyncMock(return_value=catalog)),
            patch.object(
                sgs,
                "_resolve_attach_mappings",
                AsyncMock(
                    return_value=(
                        [{"unit_index": 0, "slug": "present_simple", "exclude": False}],
                        False,
                    )
                ),
            ),
            patch.object(sgs, "_recompute_primary_sources", AsyncMock()),
        ):
            return await sgs.sync_skills_from_preview(db, 48)

    _sources, meta = asyncio.run(run())

    enrich.assert_awaited_once_with(db, 48, force=True)
    assert meta["enriched"] == 1
    assert meta["method_counts"]["heuristic"] == 1
    assert meta["edge_count_added"] == 0


def test_sync_skills_enrich_failure_sets_incomplete():
    book = MagicMock()
    book.id = 48
    book.title = "Empower"
    book.status = BookStatusEnum.ready
    book.cefr_level = CEFRLevel.A2
    book.book_type = None

    unit = MagicMock()
    unit.id = 1
    unit.title = "Present simple"
    unit.unit_index = 0
    unit.depth_or_source = "toc"
    unit.language_focus = None
    unit.grammar_cues = None
    unit.vocab_cues = None
    unit.content_summary = None

    catalog = [
        {
            "id": 99,
            "slug": "present_simple",
            "title": "Present simple",
            "difficulty_in_level": 1,
        }
    ]
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    async def run():
        with (
            patch.object(sgs.settings, "UNIT_ENRICH_ENABLED", True),
            patch.object(
                sgs, "_load_ready_book_and_units", AsyncMock(return_value=(book, [unit]))
            ),
            patch(
                "app.services.unit_enrichment_service.enrich_units_for_book",
                AsyncMock(side_effect=RuntimeError("mongo down")),
            ),
            patch.object(sgs, "load_catalog_skills", AsyncMock(return_value=catalog)),
            patch.object(
                sgs,
                "_resolve_attach_mappings",
                AsyncMock(
                    return_value=(
                        [{"unit_index": 0, "slug": "present_simple", "exclude": False}],
                        False,
                    )
                ),
            ),
            patch.object(sgs, "_recompute_primary_sources", AsyncMock()),
        ):
            return await sgs.sync_skills_from_preview(db, 48)

    _sources, meta = asyncio.run(run())

    assert meta["enrichment_incomplete"] is True
    assert meta["edge_count_added"] == 0


def test_skill_source_payload_includes_title():
    source = MagicMock()
    source.id = 10
    source.skill_id = 42
    source.unit_id = 100
    source.unit_title = "Unit 1"
    source.section_title = None
    source.is_excluded = False
    source.is_primary = True

    payload = sgs.skill_source_payload(source, skill_title="Present simple: be")

    assert payload["skill_title"] == "Present simple: be"
    assert payload["skill_id"] == 42
    assert payload["unit_id"] == 100
    assert payload["is_primary"] is True


def test_list_book_skill_sources_returns_titles_and_unmapped():
    book = MagicMock()
    book.id = 48

    unit_mapped = MagicMock()
    unit_mapped.id = 100
    unit_mapped.unit_index = 0
    unit_mapped.title = "Present simple"

    unit_unmapped = MagicMock()
    unit_unmapped.id = 101
    unit_unmapped.unit_index = 1
    unit_unmapped.title = "Dragons chapter"

    source = MagicMock()
    source.id = 10
    source.skill_id = 42
    source.unit_id = 100
    source.unit_title = "Present simple"
    source.section_title = None
    source.is_excluded = False
    source.is_primary = True

    result_units = MagicMock()
    result_units.scalars.return_value.all.return_value = [unit_mapped, unit_unmapped]

    result_sources = MagicMock()
    result_sources.all.return_value = [(source, "Present simple: be")]

    result_book = MagicMock()
    result_book.scalar_one_or_none.return_value = book

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[result_book, result_units, result_sources])

    data = asyncio.run(sgs.list_book_skill_sources(db, 48))

    assert data["book_id"] == 48
    assert data["source_count"] == 1
    assert data["mapped_count"] == 1
    assert data["sources"][0]["skill_title"] == "Present simple: be"
    assert data["unmapped_units"] == [
        {"unit_index": 1, "unit_title": "Dragons chapter"}
    ]


def test_list_book_skill_sources_empty_when_never_attached():
    book = MagicMock()
    book.id = 48

    unit = MagicMock()
    unit.id = 100
    unit.unit_index = 0
    unit.title = "Present simple"

    result_units = MagicMock()
    result_units.scalars.return_value.all.return_value = [unit]

    result_sources = MagicMock()
    result_sources.all.return_value = []

    result_book = MagicMock()
    result_book.scalar_one_or_none.return_value = book

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[result_book, result_units, result_sources])

    data = asyncio.run(sgs.list_book_skill_sources(db, 48))

    assert data["sources"] == []
    assert data["unmapped_units"] == []
    assert data["source_count"] == 0
