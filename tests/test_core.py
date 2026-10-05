from __future__ import annotations

import json
from pathlib import Path

from lwr.client import LLMClient
from lwr.experiment import LWRExperiment


def test_data_is_complete():
    root = Path(__file__).parents[1]
    curriculum = json.loads((root / "data" / "curriculum.json").read_text())
    evaluation = json.loads((root / "data" / "evaluation.json").read_text())
    assert len(curriculum) >= 12
    assert len(evaluation) >= 8
    assert any(x["domain"] == "coding" for x in curriculum)
    assert any(x["domain"] == "interface" for x in curriculum)


def _stub_json_complete(system: str, user: str) -> dict:
    """Deterministic offline stand-in so unit tests do not call a real API."""
    s = user.lower()
    if "generate a single candidate guess" in s:
        return {"statement": "Important state transitions need reliable evidence.", "source_experience_ids": []}
    if "refutation" in s and "guess" in s:
        return {"kind": "boundary_case", "challenge": "Find a counterexample.", "verdict": "needs_narrowing", "evidence": "Only important transitions need evidence."}
    if "principle" in s and "guess" in s:
        return {"statement": "Actors need reliable evidence of important state transitions.", "hostile_survival": 3, "cross_domain_count": 2, "prediction_successes": 2, "reconstruction_successes": 2, "failures": 0}
    return {"observation": "o", "outcome": "x", "tags": []}


def test_critical_comparison_uses_same_reflection(monkeypatch):
    root = Path(__file__).parents[1]
    client = LLMClient()
    monkeypatch.setattr(client, "json_complete", _stub_json_complete)
    exp = LWRExperiment(root / "data", client, max_guesses=2, refutations_per_guess=1, top_k=2)
    curriculum, _ = exp.load()
    experiences = exp.collect_experiences(curriculum[:4])
    guesses, refs, principles, world = exp.reflect(experiences)
    retention = {"experiences": experiences, "principles": principles, "world_model": world.principles}
    forgetting = {"experiences": [], "principles": principles, "world_model": world.principles}
    assert [p.id for p in retention["principles"]] == [p.id for p in forgetting["principles"]]
    assert [p.rank for p in retention["principles"]] == [p.rank for p in forgetting["principles"]]
    assert len(retention["experiences"]) > len(forgetting["experiences"])
