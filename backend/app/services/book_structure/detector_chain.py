from app.services.book_structure.base import DetectionResult, StructureDetector
from app.services.book_structure.font_style_detector import FontStyleDetector
from app.services.book_structure.regex_detector import RegexDetector
from app.services.book_structure.toc_detector import TocDetector

CONFIDENCE_THRESHOLD = 0.5


class StructureDetectorChain:
    def __init__(self, detectors: list[StructureDetector] | None = None) -> None:
        self.detectors = detectors or [
            TocDetector(),
            RegexDetector(),
            FontStyleDetector(),
        ]

    def detect_all(self, pdf_path: str) -> list[DetectionResult]:
        """Run every detector and return all non-empty results (no early exit)."""
        results: list[DetectionResult] = []
        for detector in self.detectors:
            result = detector.detect(pdf_path)
            if result is not None and result.units:
                results.append(result)
        return results

    def detect(self, pdf_path: str) -> DetectionResult | None:
        best_below_threshold: DetectionResult | None = None

        for detector in self.detectors:
            result = detector.detect(pdf_path)
            if result is None:
                continue
            if result.confidence >= CONFIDENCE_THRESHOLD:
                return result
            if best_below_threshold is None or result.confidence > best_below_threshold.confidence:
                best_below_threshold = result

        return best_below_threshold
