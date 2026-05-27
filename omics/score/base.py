"""Abstract scoring framework. Every scorer returns ScoreResult: score + explanation."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List


class ScoreCategory(str, Enum):
    IMMUNE_INFILTRATION = "immune_infiltration"
    PATHWAY_ACTIVITY = "pathway_activity"
    CELL_STATE = "cell_state"
    CLONAL_EXPANSION = "clonal_expansion"
    SPATIAL_NICHE = "spatial_niche"
    DRUG_RESPONSE = "drug_response"
    PROGNOSTIC_RISK = "prognostic_risk"
    INTEGRATED_HEALTH = "integrated_health"


@dataclass
class ScoreResult:
    score: float
    category: ScoreCategory
    confidence: float = 1.0
    contributing_features: List[str] = field(default_factory=list)
    interpretation: str = ""


class AbstractScoring(ABC):
    category: ScoreCategory

    @abstractmethod
    def compute(self, data: Any, **kwargs) -> ScoreResult:
        ...

    def explain(self, result: ScoreResult) -> str:
        if not result.interpretation:
            features = ", ".join(result.contributing_features[:10])
            result.interpretation = (
                f"[{result.category.value}] Score: {result.score:.3f} "
                f"(confidence: {result.confidence:.2f}). "
                f"Top contributing features: {features or 'none identified'}."
            )
        return result.interpretation
