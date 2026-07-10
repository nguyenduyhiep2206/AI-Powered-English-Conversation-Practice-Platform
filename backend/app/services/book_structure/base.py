from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DetectedUnit:
    title: str
    page_start: int
    page_end: int
    depth_or_source: str | None = None


@dataclass
class DetectionResult:
    method: str
    confidence: float
    units: list[DetectedUnit] = field(default_factory=list)


class StructureDetector(ABC):
    name: str

    @abstractmethod
    def detect(self, pdf_path: str) -> DetectionResult | None:
        """Return a detection result, or None if this strategy does not apply."""
