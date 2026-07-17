from app.services.book_structure.regex_detector import RegexDetector


def test_regex_detector_finds_passage_headings(regex_pdf):
  result = RegexDetector().detect(str(regex_pdf))

  assert result is not None
  assert result.method == "regex"
  assert result.confidence == 0.6
  assert len(result.units) == 3
  assert result.units[0].title.startswith("PASSAGE 1")


def test_regex_detector_returns_none_for_plain_pdf(tmp_path):
  from pypdf import PdfWriter

  path = tmp_path / "plain.pdf"
  writer = PdfWriter()
  writer.add_blank_page(612, 792)
  with path.open("wb") as handle:
    writer.write(handle)

  assert RegexDetector().detect(str(path)) is None


def test_regex_detector_accepts_passage_typos_and_casing(passage_variant_pdf):
  result = RegexDetector().detect(str(passage_variant_pdf))

  assert result is not None
  assert len(result.units) == 3
  titles = [unit.title.upper() for unit in result.units]
  assert any("PASSSAGE 1" in title or "PASSAGE 1" in title for title in titles)
  assert any("PASSAGE 2" in title for title in titles)
  assert any("PASSAGE 3" in title for title in titles)


def test_regex_detector_skips_dense_overview_pages(overview_then_content_pdf):
  result = RegexDetector().detect(str(overview_then_content_pdf))

  assert result is not None
  # Overview page packs many headings; keep only real content pages.
  assert all(unit.page_start > 1 for unit in result.units)
  assert len(result.units) >= 3
  assert result.units[0].title.startswith("Unit 1")


def test_regex_detector_keeps_passage_when_test_shares_page(test_and_passage_pdf):
  result = RegexDetector().detect(str(test_and_passage_pdf))

  assert result is not None
  assert len(result.units) == 3
  assert all("PASSAGE" in unit.title.upper() for unit in result.units)


def test_regex_detector_finds_numbered_all_caps_passages(numbered_caps_passage_pdf):
  result = RegexDetector().detect(str(numbered_caps_passage_pdf))

  assert result is not None
  assert result.method == "regex"
  assert len(result.units) == 3
  assert result.units[0].title.startswith("1.")
  assert "OLD MAN" in result.units[0].title.upper()
  assert result.units[0].page_start == 1
  assert result.units[2].page_start == 3
