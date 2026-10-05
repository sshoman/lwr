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


def test_critical_comparison_uses_same_reflection(monkeypatch):
    root = Path(__file__).parents[1]
    exp = LWRExperiment(root / "data", LLMClient(mock=True), max_guesses=2, refutations_per_guess=1, top_k=2)
    curriculum, _ = exp.load()
    experiences = exp.collect_experiences(curriculum[:4])
    guesses, refs, principles, world = exp.reflect(experiences)
    retention = {"experiences": experiences, "principles": principles, "world_model": world.principles}
    forgetting = {"experiences": [], "principles": principles, "world_model": world.principles}
    assert [p.id for p in retention["principles"]] == [p.id for p in forgetting["principles"]]
    assert [p.rank for p in retention["principles"]] == [p.rank for p in forgetting["principles"]]
    assert len(retention["experiences"]) > len(forgetting["experiences"])


def test_mock_run_smoke(tmp_path):
    root = Path(__file__).parents[1]
    exp = LWRExperiment(root / "data", LLMClient(mock=True), max_guesses=2, refutations_per_guess=1, top_k=2)
    result = exp.run()
    assert set(result["results"]) == {"base", "summary", "reflective_retention", "reflective_forgetting"}
    for row in result["results"].values():
        assert 0 <= row["score"] <= 1
