from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .client import LLMClient
from .core import ConditionResult, Experience, Guess, Principle, Refutation, WorldModel
from .prompts import (
    decision_prompt,
    experience_agent_prompt,
    guess_prompt,
    principle_prompt,
    refutation_prompt,
    summary_prompt,
)


CONDITIONS = [
    "base",
    "summary",
    "reflective_retention",
    "reflective_forgetting",
]


class LWRExperiment:
    def __init__(self, data_dir: str | Path, client: LLMClient, max_guesses: int = 6, refutations_per_guess: int = 4, top_k: int = 6):
        self.data_dir = Path(data_dir)
        self.client = client
        self.max_guesses = max_guesses
        self.refutations_per_guess = refutations_per_guess
        self.top_k = top_k

    def load(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        curriculum = json.loads((self.data_dir / "curriculum.json").read_text())
        evaluation = json.loads((self.data_dir / "evaluation.json").read_text())
        return curriculum, evaluation

    def collect_experiences(self, curriculum: list[dict[str, Any]]) -> list[Experience]:
        experiences: list[Experience] = []
        for case in curriculum:
            system, user = experience_agent_prompt(case)
            out = self.client.json_complete(system, user)
            experiences.append(
                Experience(
                    id=f"EXP-{case['id']}",
                    domain=case["domain"],
                    title=case["title"],
                    scenario=case["scenario"],
                    observed=out.get("observation", ""),
                    outcome=out.get("outcome", case.get("outcome", "")),
                    tags=list(out.get("tags", case.get("tags", []))),
                )
            )
        return experiences

    def reflect(self, experiences: list[Experience]) -> tuple[list[Guess], list[Refutation], list[Principle], WorldModel]:
        exp_dicts = [asdict(e) for e in experiences]
        guesses: list[Guess] = []
        refutations: list[Refutation] = []
        principles: list[Principle] = []

        chunks = self._chunks(exp_dicts, self.max_guesses)
        for idx, chunk in enumerate(chunks):
            system, user = guess_prompt(chunk)
            out = self.client.json_complete(system, user)
            g = Guess(
                id=f"G-{idx+1}",
                statement=str(out.get("statement", "")),
                source_experience_ids=list(out.get("source_experience_ids", [])),
            )
            if not g.statement:
                continue
            guesses.append(g)

            prior_attacks: list[dict[str, Any]] = []
            for j in range(self.refutations_per_guess):
                system, user = refutation_prompt(asdict(g), exp_dicts, prior_attacks)
                attack = self.client.json_complete(system, user)
                r = Refutation(
                    id=f"R-{idx+1}-{j+1}",
                    guess_id=g.id,
                    kind=str(attack.get("kind", "counterexample")),
                    challenge=str(attack.get("challenge", "")),
                    verdict=str(attack.get("verdict", "needs_narrowing")),
                    evidence=str(attack.get("evidence", "")),
                )
                refutations.append(r)
                prior_attacks.append(asdict(r))

            attacks = [asdict(r) for r in refutations if r.guess_id == g.id]
            if sum(r["verdict"] == "fails" for r in attacks) >= 2:
                g.status = "killed"
                continue
            if any(r["verdict"] == "needs_narrowing" for r in attacks):
                g.status = "refined"
            psys, puser = principle_prompt(asdict(g), attacks)
            pout = self.client.json_complete(psys, puser)
            principles.append(
                Principle(
                    id=f"P-{idx+1}",
                    statement=str(pout.get("statement", g.statement)),
                    source_guess_ids=[g.id],
                    rank=self._rank(pout),
                    cross_domain_count=int(pout.get("cross_domain_count", 0)),
                    hostile_survival=int(pout.get("hostile_survival", 0)),
                    prediction_successes=int(pout.get("prediction_successes", 0)),
                    reconstruction_successes=int(pout.get("reconstruction_successes", 0)),
                    failures=int(pout.get("failures", 0)),
                )
            )

        world = WorldModel(principles=principles).top(self.top_k)
        return guesses, refutations, principles, WorldModel(world)

    @staticmethod
    def _rank(data: dict[str, Any]) -> float:
        survival = float(data.get("hostile_survival", 0))
        diversity = float(data.get("cross_domain_count", 0))
        predictions = float(data.get("prediction_successes", 0))
        reconstruction = float(data.get("reconstruction_successes", 0))
        failures = float(data.get("failures", 0))
        return 2.5 * survival + 2.0 * diversity + 2.5 * predictions + 2.0 * reconstruction - 3.0 * failures

    @staticmethod
    def _chunks(items: list[dict[str, Any]], n: int) -> list[list[dict[str, Any]]]:
        if not items:
            return []
        size = max(1, (len(items) + n - 1) // n)
        return [items[i:i + size] for i in range(0, len(items), size)]

    def build_summary(self, experiences: list[Experience]) -> str:
        system, user = summary_prompt([asdict(e) for e in experiences])
        return str(self.client.json_complete(system, user).get("summary", ""))

    def run(self) -> dict[str, Any]:
        curriculum, evaluation = self.load()
        experiences = self.collect_experiences(curriculum)
        guesses, refutations, principles, world = self.reflect(experiences)
        summary = self.build_summary(experiences)

        # Critical comparison: retention and forgetting receive the exact same
        # reflective artifacts. Only episode availability changes.
        memories = {
            "base": {"experiences": [], "principles": [], "world_model": []},
            "summary": {"summary": summary, "experiences": [], "principles": [], "world_model": []},
            "reflective_retention": {
                "experiences": [asdict(e) for e in experiences],
                "principles": [asdict(p) for p in principles],
                "world_model": [asdict(p) for p in world.principles],
            },
            "reflective_forgetting": {
                "experiences": [],
                "principles": [asdict(p) for p in principles],
                "world_model": [asdict(p) for p in world.principles],
            },
        }

        results: dict[str, Any] = {}
        for condition in CONDITIONS:
            results[condition] = self.evaluate_condition(condition, evaluation, memories[condition])

        return {
            "config": {
                "conditions": CONDITIONS,
                "max_guesses": self.max_guesses,
                "refutations_per_guess": self.refutations_per_guess,
                "top_k": self.top_k,
            },
            "artifacts": {
                "experiences": [asdict(e) for e in experiences],
                "guesses": [asdict(g) for g in guesses],
                "refutations": [asdict(r) for r in refutations],
                "principles": [asdict(p) for p in principles],
                "world_model": [asdict(p) for p in world.principles],
            },
            "results": results,
        }

    def evaluate_condition(self, condition: str, evaluation: list[dict[str, Any]], memory: dict[str, Any]) -> dict[str, Any]:
        rows = []
        for case in evaluation:
            system, user = decision_prompt(case, condition, memory)
            out = self.client.json_complete(system, user)
            choice = str(out.get("choice", "")).strip().upper()
            gold = str(case["gold_choice"]).strip().upper()
            correct = choice == gold
            cited = list(out.get("cited_experience_ids", []))
            rows.append({
                "case_id": case["id"],
                "choice": choice,
                "gold_choice": gold,
                "correct": correct,
                "confidence": float(out.get("confidence", 0.0)),
                "rationale": str(out.get("rationale", "")),
                "cited_experience_ids": cited,
                "transfer": bool(case.get("transfer", True)),
                "exact_recall": bool(case.get("exact_recall", False)),
            })

        n = len(rows) or 1
        transfer_rows = [r for r in rows if r["transfer"]]
        recall_rows = [r for r in rows if r["exact_recall"]]
        transfer_score = sum(r["correct"] for r in transfer_rows) / (len(transfer_rows) or 1)
        recall_score = sum(r["correct"] for r in recall_rows) / (len(recall_rows) or 1)
        overall = sum(r["correct"] for r in rows) / n
        cited_rate = sum(bool(r["cited_experience_ids"]) for r in rows) / n
        return ConditionResult(
            condition=condition,
            decisions=rows,
            score=overall,
            exact_recall_score=recall_score,
            transfer_score=transfer_score,
            avg_confidence=sum(r["confidence"] for r in rows) / n,
            cited_episode_rate=cited_rate,
            memory_items_available=len(memory.get("experiences", [])),
            world_model_size=len(memory.get("world_model", [])),
        ).to_dict()


def save_result(result: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
