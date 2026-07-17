from app.services.book_structure.detector_chain import StructureDetectorChain


def test_chain_prefers_toc_over_regex(toc_pdf, regex_pdf):
  chain = StructureDetectorChain()

  toc_result = chain.detect(str(toc_pdf))
  assert toc_result is not None
  assert toc_result.method == "toc"
  assert toc_result.confidence >= 0.5

  regex_result = chain.detect(str(regex_pdf))
  assert regex_result is not None
  assert regex_result.method == "regex"


def test_chain_falls_through_junk_toc_to_numbered_caps(junk_toc_with_numbered_caps_pdf):
  result = StructureDetectorChain().detect(str(junk_toc_with_numbered_caps_pdf))

  assert result is not None
  assert result.method == "regex"
  assert len(result.units) == 3
  assert "OLD MAN" in result.units[0].title.upper()
  assert all("Images" not in unit.title for unit in result.units)


def test_detect_all_returns_every_non_none_result(junk_toc_with_numbered_caps_pdf):
  chain = StructureDetectorChain()
  results = chain.detect_all(str(junk_toc_with_numbered_caps_pdf))
  methods = {r.method for r in results}
  # Toc rejects junk → None; Regex finds numbered caps
  assert "regex" in methods
  assert all(r.units for r in results)


def test_detect_still_early_returns_for_backward_compat(toc_pdf):
  result = StructureDetectorChain().detect(str(toc_pdf))
  assert result is not None
  assert result.method == "toc"
