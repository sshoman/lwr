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

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig(
            model=os.getenv("LWR_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("LWR_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.rng = random.Random(7)

    def complete(self, system: str, user: str) -> str:
        if not self.config.api_key:
            raise RuntimeError("Missing OPENAI_API_KEY. Point --base-url/--model at any OpenAI-compatible endpoint.")

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
