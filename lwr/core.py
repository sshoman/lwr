from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Literal

Stage = Literal["guess", "principle"]


@dataclass
class Experience:
    id: str
    domain: str
    title: str
    scenario: str
    observed: str
    outcome: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Guess:
    id: str
    statement: str
    source_experience_ids: list[str]
    status: Literal["alive", "killed", "refined"] = "alive"


@dataclass
class Refutation:
    id: str
    guess_id: str
    kind: str
    challenge: str
    verdict: Literal["survives", "fails", "needs_narrowing"]
    evidence: str


@dataclass
class Principle:
    id: str
    statement: str
    source_guess_ids: list[str]
    rank: float = 0.0
    cross_domain_count: int = 0
    hostile_survival: int = 0
    prediction_successes: int = 0
    reconstruction_successes: int = 0
    failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorldModel:
    principles: list[Principle] = field(default_factory=list)

    def top(self, k: int = 8) -> list[Principle]:
        return sorted(self.principles, key=lambda p: p.rank, reverse=True)[:k]


@dataclass
class ExperimentCase:
    id: str
    domain: str
    scenario: str
    choices: list[str]
    gold_choice: str
    transfer_tag: str
    explanation: str
    exact_recall: bool = False
    training: bool = False


@dataclass
class Decision:
    case_id: str
    choice: str
    confidence: float
    rationale: str
    cited_experience_ids: list[str] = field(default_factory=list)

    @property
    def correct(self) -> bool:
        return bool(self.choice)


@dataclass
class ConditionResult:
    condition: str
    decisions: list[dict[str, Any]]
    score: float
    exact_recall_score: float
    transfer_score: float
    avg_confidence: float
    cited_episode_rate: float
    memory_items_available: int
    world_model_size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
