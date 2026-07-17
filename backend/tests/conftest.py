from pathlib import Path

import pytest

from tests.fixtures.pdf_factory import (
  make_accessibility_outline_pdf,
  make_chapter_outline_pdf,
  make_font_heading_pdf,
  make_junk_toc_with_numbered_caps_pdf,
  make_numbered_caps_passage_pdf,
  make_overview_then_content_pdf,
  make_passage_variant_pdf,
  make_regex_pdf,
  make_test_and_passage_same_page_pdf,
  make_toc_pdf,
)


@pytest.fixture
def toc_pdf(tmp_path: Path) -> Path:
  return make_toc_pdf(tmp_path / "toc.pdf")


@pytest.fixture
def regex_pdf(tmp_path: Path) -> Path:
  return make_regex_pdf(tmp_path / "regex.pdf")


@pytest.fixture
def font_pdf(tmp_path: Path) -> Path:
  return make_font_heading_pdf(tmp_path / "font.pdf")


@pytest.fixture
def passage_variant_pdf(tmp_path: Path) -> Path:
  return make_passage_variant_pdf(tmp_path / "passage_variant.pdf")


@pytest.fixture
def overview_then_content_pdf(tmp_path: Path) -> Path:
  return make_overview_then_content_pdf(tmp_path / "overview_content.pdf")


@pytest.fixture
def test_and_passage_pdf(tmp_path: Path) -> Path:
  return make_test_and_passage_same_page_pdf(tmp_path / "test_passage.pdf")


@pytest.fixture
def chapter_outline_pdf(tmp_path: Path) -> Path:
  return make_chapter_outline_pdf(tmp_path / "chapter_outline.pdf")


@pytest.fixture
def accessibility_outline_pdf(tmp_path: Path) -> Path:
  return make_accessibility_outline_pdf(tmp_path / "accessibility_outline.pdf")


@pytest.fixture
def numbered_caps_passage_pdf(tmp_path: Path) -> Path:
  return make_numbered_caps_passage_pdf(tmp_path / "numbered_caps.pdf")


@pytest.fixture
def junk_toc_with_numbered_caps_pdf(tmp_path: Path) -> Path:
  return make_junk_toc_with_numbered_caps_pdf(tmp_path / "junk_toc_caps.pdf")
