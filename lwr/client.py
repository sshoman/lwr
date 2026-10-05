from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib import request


@dataclass
class LLMConfig:
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    temperature: float = 0.2
    timeout: int = 120


class LLMClient:
    """Tiny OpenAI-compatible client. It intentionally has no framework dependency."""

    def __init__(self, config: LLMConfig | None = None, mock: bool = False):
        self.config = config or LLMConfig(
            model=os.getenv("LWR_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("LWR_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.mock = mock or os.getenv("LWR_MOCK", "0") == "1"
        self.rng = random.Random(7)

    def complete(self, system: str, user: str) -> str:
        if self.mock:
            return self._mock(system, user)
        if not self.config.api_key:
            raise RuntimeError("Missing OPENAI_API_KEY (or set LWR_MOCK=1 for a local smoke test).")

        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.config.temperature,
        }
        data = json.dumps(body).encode("utf-8")
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        req = request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )
        for attempt in range(3):
            try:
                with request.urlopen(req, timeout=self.config.timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                return payload["choices"][0]["message"]["content"]
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise AssertionError("unreachable")

    def json_complete(self, system: str, user: str) -> dict[str, Any]:
        raw = self.complete(system, user)
        raw = raw.strip()
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if not match:
            raise ValueError(f"Model did not return JSON: {raw}")
        return json.loads(match.group(0))

    def _mock(self, system: str, user: str) -> str:
        s = user.lower()
        # Order matters: a decision prompt also mentions principles, experience
        # ids, and summaries, so it must be matched before those branches.
        if "choose the best option" in s:
            return json.dumps(self._mock_decision(user))
        if "generate a single candidate guess" in s:
            return json.dumps({
                "statement": "Important state transitions need reliable evidence before the next decision.",
                "source_experience_ids": re.findall(r"EXP-[A-Z0-9-]+", user)[:3],
            })
        if "refutation" in s and "guess" in s:
            return json.dumps({
                "kind": "boundary_case",
                "challenge": "Find a case where the proposed rule should not hold.",
                "verdict": "needs_narrowing",
                "evidence": "A silent operation can be fine when the actor does not need evidence of an important state transition.",
            })
        if "principle" in s and "guess" in s:
            return json.dumps({
                "statement": "Actors need reliable evidence of important state transitions before making the next decision.",
                "hostile_survival": 3,
                "cross_domain_count": 2,
                "prediction_successes": 2,
                "reconstruction_successes": 2,
                "failures": 0,
            })
        if "summary" in s:
            return json.dumps({"summary": "Carry forward the structural lessons and their boundaries."})
        return json.dumps({"text": "mock"})

    def _mock_decision(self, user: str) -> dict[str, Any]:
        """Deterministic answer heuristic for mock mode.

        The mock is not trying to be a smart model. It simulates the qualitative
        pattern the paper predicts so the pipeline can be smoke-tested offline:
        conditions with real principles/world model answer transfer cases with
        the principle-aligned option, and exact-recall cases are answered
        correctly only when raw episodes are still in memory.
        """
        recall_case = '"exact_recall": true' in user
        has_episodes = '"experiences": []' not in user
        has_principles = '"principles": []' not in user or '"world_model": []' not in user

        if recall_case:
            if has_episodes:
                choice = self._mock_recall_choice(user)
            else:
                choice = "C"
        elif has_principles:
            choice = "B"
        elif '"summary": "' in user:
            # Summaries carry the gist but less structure; right only half the time.
            choice = "B" if (sum(ord(c) for c in user) % 2 == 0) else "A"
        else:
            choice = "A"
        return {
            "choice": choice,
            "confidence": 0.72,
            "rationale": "The structural pattern matters more than the surface details.",
            "cited_experience_ids": re.findall(r"EXP-[A-Z0-9-]+", user)[:1] if has_episodes and recall_case else [],
        }

    def _mock_recall_choice(self, user: str) -> str:
        """Match the recall question against episode titles in memory."""
        scenario = ""
        m = re.search(r'"scenario": "(.*?)"', user, flags=re.S)
        if m:
            scenario = m.group(1).lower()
        best_id, best_score = None, 0
        for tid, title in re.findall(r'"id": "EXP-([A-Z0-9-]+)".*?"title": "(.*?)"', user, flags=re.S):
            words = [w for w in re.split(r"\W+", title.lower()) if len(w) > 3]
            score = sum(w in scenario for w in words)
            if score > best_score:
                best_id, best_score = tid, score
        if best_id is None:
            return "C"
        for letter, cid in re.findall(r'"([A-Z]): (C\d+)"', user):
            if cid == best_id:
                return letter
        return "C"
