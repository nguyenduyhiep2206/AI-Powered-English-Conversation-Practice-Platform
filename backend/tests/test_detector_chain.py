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
