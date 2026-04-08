from enum import Enum
from dataclasses import dataclass
class Override(Enum):
    BASELINE = "baseline"
    STRUCTURED_OVERRIDE = "structured_override"


@dataclass(frozen=True)
class Run:
    scenario: str
    override_type: Override
    model: str  # must be a key of MODEL_REGISTRY
