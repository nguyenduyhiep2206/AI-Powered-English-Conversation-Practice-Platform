from app.services.book_structure.toc_detector import TocDetector


def test_toc_detector_finds_numbered_subsections(toc_pdf):
  result = TocDetector().detect(str(toc_pdf))

  assert result is not None
  assert result.method == "toc"
  assert result.confidence >= 0.7
  assert len(result.units) >= 3
  assert result.units[0].title.startswith("1.1")
  assert result.units[0].page_start == 2
  assert result.units[0].page_end == 2


def test_toc_detector_returns_none_without_outline(tmp_path):
  from pypdf import PdfWriter

  path = tmp_path / "blank.pdf"
  writer = PdfWriter()
  writer.add_blank_page(612, 792)
  with path.open("wb") as handle:
    writer.write(handle)

  assert TocDetector().detect(str(path)) is None


def test_toc_detector_prefers_chapter_headings_over_front_matter(chapter_outline_pdf):
  result = TocDetector().detect(str(chapter_outline_pdf))

  assert result is not None
  assert result.method == "toc"
  assert len(result.units) >= 4
  assert all(unit.title.startswith("Chapter ") for unit in result.units)
  assert result.units[0].page_start == 6


def test_toc_detector_rejects_accessibility_outline_junk(accessibility_outline_pdf):
  assert TocDetector().detect(str(accessibility_outline_pdf)) is None
