from __future__ import annotations

import json
from typing import Any


def _dump(x: Any) -> str:
    return json.dumps(x, indent=2, ensure_ascii=False)


def experience_agent_prompt(case: dict[str, Any]) -> tuple[str, str]:
    return (
        "You are the active agent collecting experience for a learning experiment. "
        "Act on the case, then record what happened. Do not invent hidden facts.",
        "CASE:\n" + _dump(case) + "\n\nReturn JSON with: observation, decision, outcome, tags.",
    )


def summary_prompt(experiences: list[dict[str, Any]]) -> tuple[str, str]:
    return (
        "You compress experience into a short working summary. Preserve useful patterns, "
        "important exceptions, and uncertainty. Do not turn guesses into facts.",
        "EXPERIENCES:\n" + _dump(experiences) + "\n\nReturn JSON: {summary: string}.",
    )


def guess_prompt(experiences: list[dict[str, Any]]) -> tuple[str, str]:
    return (
        "You are Shaman, the slow reflective layer. Make a cheap tentative guess about a "
        "mechanic that may explain multiple experiences. Do not write a polished universal law. "
        "A guess is allowed to be wrong.",
        "EXPERIENCES:\n" + _dump(experiences) + "\n\n" 
        "Generate a single candidate guess. Return JSON: {statement, source_experience_ids}.",
    )


def refutation_prompt(guess: dict[str, Any], experiences: list[dict[str, Any]], prior: list[dict[str, Any]]) -> tuple[str, str]:
    return (
        "You are trying to kill a hypothesis, not support it. Search for counterexamples, "
        "boundary cases, reversals, competing explanations, failed predictions, or another domain "
        "where it should break. Be hostile.",
        "GUESS:\n" + _dump(guess) + "\n\n" 
        "EXPERIENCES:\n" + _dump(experiences) + "\n\n"
        "PRIOR ATTACKS:\n" + _dump(prior) + "\n\n"
        "Return JSON: {kind, challenge, verdict, evidence} where verdict is survives, fails, or needs_narrowing.",
    )


def principle_prompt(guess: dict[str, Any], refutations: list[dict[str, Any]]) -> tuple[str, str]:
    return (
        "Turn a surviving guess into a principle only if the attacks did not kill it. "
        "Make it more precise, include boundaries, and keep it transferable. Do not reward frequency alone.",
        "GUESS:\n" + _dump(guess) + "\n\nREFUTATIONS:\n" + _dump(refutations) + "\n\n"
        "Return JSON: {statement, hostile_survival, cross_domain_count, prediction_successes, reconstruction_successes, failures}.",
    )


def decision_prompt(case: dict[str, Any], condition: str, memory: dict[str, Any]) -> tuple[str, str]:
    system = (
        "You are the active agent in a controlled generalization experiment. "
        "Solve the new task using your base knowledge plus the supplied condition-specific memory. "
        "Do not claim to remember information that is not present. Return JSON only."
    )
    agent_case = {k: v for k, v in case.items() if k not in ("gold_choice", "explanation")}
    user = (
        f"CONDITION: {condition}\n"
        f"TASK:\n{_dump(agent_case)}\n\n"
        f"AVAILABLE MEMORY:\n{_dump(memory)}\n\n"
        "Choose the best option. Return JSON: {choice, confidence, rationale, cited_experience_ids}."
    )
    return system, user
