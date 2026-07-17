"""Helpers to build small PDF files for structure-detector tests."""

from pathlib import Path

from pypdf import PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_toc_pdf(path: Path, num_pages: int = 6) -> Path:
  """PDF with outline entries like 1.1 / 1.2 at depth 1."""
  writer = PdfWriter()
  for _ in range(num_pages):
    writer.add_blank_page(612, 792)

  chapter1 = writer.add_outline_item("Chapter 1", 0)
  writer.add_outline_item("1.1 Present Perfect", 1, parent=chapter1)
  writer.add_outline_item("1.2 Past Simple", 2, parent=chapter1)
  chapter2 = writer.add_outline_item("Chapter 2", 3)
  writer.add_outline_item("2.1 Conditionals", 4, parent=chapter2)
  writer.add_outline_item("2.2 Modals", 5, parent=chapter2)

  with path.open("wb") as handle:
    writer.write(handle)
  return path


def make_regex_pdf(path: Path) -> Path:
  """PDF whose page text matches PASSAGE headings."""
  c = canvas.Canvas(str(path), pagesize=letter)
  passages = [
    "PASSAGE 1: Daily Routine",
    "Body text for passage one.",
    "PASSAGE 2: Workplace Email",
    "Body text for passage two.",
    "PASSAGE 3: Travel Dialog",
    "Body text for passage three.",
  ]
  for index, line in enumerate(passages):
    if index % 2 == 0:
      c.setFont("Helvetica-Bold", 14)
    else:
      c.setFont("Helvetica", 11)
    c.drawString(72, 720, line)
    c.showPage()
  c.save()
  return path


def make_font_heading_pdf(path: Path) -> Path:
  """PDF with large bold headings and smaller body text."""
  c = canvas.Canvas(str(path), pagesize=letter)
  pages = [
    ("Unit Overview", "This is regular body text on page one."),
    ("Grammar Focus", "More body text on page two."),
    ("Practice Section", "Even more body text on page three."),
  ]
  for heading, body in pages:
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 750, heading)
    c.setFont("Helvetica", 11)
    c.drawString(72, 720, body)
    c.showPage()
  c.save()
  return path


def make_passage_variant_pdf(path: Path) -> Path:
  """PASSAGE headings with mixed casing and a common typo."""
  c = canvas.Canvas(str(path), pagesize=letter)
  headings = [
    "PASSSAGE 1: Reducing the Effects",
    "PASSAGE 2: Raising the Mary",
    "Passage 3: Neuroaesthetics",
  ]
  for heading in headings:
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, heading)
    c.setFont("Helvetica", 11)
    c.drawString(72, 690, "Body text for this passage.")
    c.showPage()
  c.save()
  return path


def make_overview_then_content_pdf(path: Path) -> Path:
  """Page 1 is a dense TOC/overview; later pages have real single headings."""
  c = canvas.Canvas(str(path), pagesize=letter)

  c.setFont("Helvetica-Bold", 14)
  c.drawString(72, 750, "Section Overview")
  overview_lines = [
    "Unit 1: Psychology",
    "Chapter 1: Dreams",
    "Chapter 2: Coping",
    "Chapter 3: Thinking and Learning",
  ]
  y = 720
  for line in overview_lines:
    c.setFont("Helvetica", 11)
    c.drawString(72, y, line)
    y -= 18
  c.showPage()

  content_pages = [
    "Unit 1: Psychology",
    "Chapter 1: Dreams",
    "Chapter 2: Coping",
    "Chapter 3: Thinking and Learning",
  ]
  for heading in content_pages:
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, heading)
    c.setFont("Helvetica", 11)
    c.drawString(72, 690, "Real chapter body text.")
    c.showPage()
  c.save()
  return path


def make_test_and_passage_same_page_pdf(path: Path) -> Path:
  """TEST + PASSAGE on same page should keep PASSAGE, not drop the page."""
  c = canvas.Canvas(str(path), pagesize=letter)
  pages = [
    ("TEST 1", "PASSAGE 1: Crop Growing"),
    ("TEST 2", "PASSAGE 2: Falkirk Wheel"),
    ("TEST 3", "PASSAGE 3: Reducing Effects"),
  ]
  for test_line, passage_line in pages:
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, test_line)
    c.drawString(72, 690, passage_line)
    c.setFont("Helvetica", 11)
    c.drawString(72, 660, "Body text.")
    c.showPage()
  c.save()
  return path


def make_chapter_outline_pdf(path: Path, num_pages: int = 30) -> Path:
  """Outline with front-matter at depth 0 and Chapter N at depth 1."""
  writer = PdfWriter()
  for _ in range(num_pages):
    writer.add_blank_page(612, 792)

  writer.add_outline_item("Cover Page", 0)
  writer.add_outline_item("Title Page", 1)
  writer.add_outline_item("Contents", 2)
  writer.add_outline_item("Preface", 3)
  writer.add_outline_item("Chapter 1: An overview of English grammar", 5)
  writer.add_outline_item("Chapter 2: Word structure and word-formation", 10)
  writer.add_outline_item("Chapter 3: Word classes and simple phrases", 15)
  writer.add_outline_item("Chapter 4: Grammatical functions", 20)
  writer.add_outline_item("Chapter 5: Complex phrases and coordination", 25)

  with path.open("wb") as handle:
    writer.write(handle)
  return path


def make_accessibility_outline_pdf(path: Path, num_pages: int = 52) -> Path:
  """Broken outline like OER accessibility bookmarks (not real chapter TOC)."""
  writer = PdfWriter()
  for _ in range(num_pages):
    writer.add_blank_page(612, 792)

  access = writer.add_outline_item("Accessibility Statement", 3)
  writer.add_outline_item("Multiple File Formats Available", 3, parent=access)
  writer.add_outline_item("Organization of content", 3, parent=access)
  writer.add_outline_item("Images", 3, parent=access)
  writer.add_outline_item("Links", 3, parent=access)
  writer.add_outline_item("Font Size and formatting", 4, parent=access)
  writer.add_outline_item("Known Issues/Potential barriers to accessibility", 4, parent=access)

  with path.open("wb") as handle:
    writer.write(handle)
  return path


def make_numbered_caps_passage_pdf(path: Path) -> Path:
  """Headings like Daily Departures: '1' then ALL-CAPS title."""
  c = canvas.Canvas(str(path), pagesize=letter)
  passages = [
    ("1", "THE OLD MAN WAITS AT THE POST OFFICE"),
    ("2", "DON\u2019T WEAR HEADPHONES WHILE DRIVING"),
    ("3", "MAX THE CAT"),
  ]
  for number, title in passages:
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 750, number)
    c.drawString(72, 730, title)
    c.setFont("Helvetica", 11)
    c.drawString(72, 700, "Body text for this reading passage.")
    c.showPage()
  c.save()
  return path


def make_junk_toc_with_numbered_caps_pdf(path: Path) -> Path:
  """Accessibility outline (should be rejected) + numbered ALL-CAPS body headings."""
  make_numbered_caps_passage_pdf(path)
  writer = PdfWriter()
  writer.append(str(path))
  access = writer.add_outline_item("Accessibility Statement", 0)
  writer.add_outline_item("Multiple File Formats Available", 0, parent=access)
  writer.add_outline_item("Images", 0, parent=access)
  writer.add_outline_item("Links", 1, parent=access)
  writer.add_outline_item("Font Size and formatting", 1, parent=access)
  writer.add_outline_item("Known Issues/Potential barriers to accessibility", 2, parent=access)
  with path.open("wb") as handle:
    writer.write(handle)
  return path
