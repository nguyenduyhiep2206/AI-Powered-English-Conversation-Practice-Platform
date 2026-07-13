from app.services.book_structure.font_style_detector import FontStyleDetector


def test_font_style_detector_finds_headings(font_pdf):
  result = FontStyleDetector().detect(str(font_pdf))

  assert result is not None
  assert result.method == "font_style"
  assert result.confidence == 0.4
  assert len(result.units) >= 2
