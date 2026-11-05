from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib import error, request
import importlib.util

MODEL_ID = os.getenv("SHAMAN_MODEL_ID", "Qwen3-4B-GGUF-Q4_K_M")
RUNNER_PATH = Path(os.getenv("SHAMAN_GEMINI_RUNNER", "runner/run.py"))
OUTPUT_DIR = Path(os.getenv("SHAMAN_OUTPUT_DIR", "shaman-results/test_001_local"))
BASE_URL = os.getenv("SHAMAN_LOCAL_LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")


class LocalLLM:
    """OpenAI-compatible client for a local llama.cpp server."""

    def __init__(self, model: str):
        self.model = model
        self.key = None
        self.usage = {
            "requests": 0,
            "successful_requests": 0,
            "retries": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def ask(self, system: str, user: str, max_tokens: int = 4500) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False},
        }
        req = request.Request(
            BASE_URL,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

        for attempt in range(4):
            self.usage["requests"] += 1
            try:
                with request.urlopen(req, timeout=600) as response:
                    result = json.loads(response.read().decode("utf-8"))
                self.usage["successful_requests"] += 1
                usage = result.get("usage") or {}
                self.usage["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
                self.usage["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
                self.usage["total_tokens"] += int(usage.get("total_tokens", 0) or 0)

                choices = result.get("choices") or []
                if not choices:
                    raise RuntimeError("Local model returned no choices.")
                message = choices[0].get("message") or {}
                content = message.get("content", "")
                if isinstance(content, list):
                    content = "\n".join(
                        str(item.get("text", ""))
                        for item in content if isinstance(item, dict)
                    )
                if not str(content).strip():
                    raise RuntimeError("Local model returned empty content.")
                return self._parse_json(str(content))
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:1500]
                if exc.code not in (408, 409, 429, 500, 502, 503, 504) or attempt == 3:
                    raise RuntimeError(f"Local llama.cpp HTTP {exc.code}: {detail}") from exc
            except (error.URLError, TimeoutError, OSError) as exc:
                if attempt == 3:
                    raise RuntimeError(f"Could not reach local llama.cpp server: {exc}") from exc
            self.usage["retries"] += 1
            time.sleep(min(12, 2 ** attempt))

        raise RuntimeError("Local model request exhausted retries.")

    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = raw.strip()
        fence = chr(96) * 3
        if text.startswith(fence):
            lines = text.splitlines()
            if lines and lines[0].startswith(fence):
                lines = lines[1:]
            if lines and lines[-1].strip() == fence:
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            if start < 0:
                raise ValueError(f"Local model did not return JSON: {text[:500]}")
            depth = 0
            quoted = False
            escaped = False
            value = None
            for index in range(start, len(text)):
                char = text[index]
                if quoted:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        quoted = False
                    continue
                if char == '"':
                    quoted = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        value = json.loads(text[start:index + 1])
                        break
            if value is None:
                raise ValueError(f"Incomplete JSON from local model: {text[:500]}")
        if not isinstance(value, dict):
            raise ValueError("Local model response must be a JSON object.")
        return value


def main() -> None:
    if not RUNNER_PATH.exists():
        raise FileNotFoundError(f"Original Test 001 runner not found: {RUNNER_PATH}")

    spec = importlib.util.spec_from_file_location("test_001_original_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load experiment runner: {RUNNER_PATH}")
    experiment = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = experiment
    spec.loader.exec_module(experiment)

    # Reuse the existing experiment and deterministic evaluator unchanged.
    experiment.Gemini = LocalLLM
    experiment.DEFAULT_MODEL = MODEL_ID

    original_save = experiment.save

    def save_with_backend_metadata(path: Path, data: dict) -> None:
        if data.get("experiment") == "test_001_refutation_transfer":
            data["execution_backend"] = {
                "provider": "local",
                "runtime": "llama.cpp on GitHub-hosted Ubuntu",
                "model": MODEL_ID,
                "model_family": "Qwen3-4B",
                "quantization": "Q4_K_M",
                "gemini_api_used": False,
            }
            if not any("local-model replication" in x for x in data.get("limitations", [])):
                data.setdefault("limitations", []).append(
                    "This is the local-model replication, not the original Gemini 3.8 run. "
                    "Results must not be pooled or directly compared with Gemini runs."
                )
            if "api_usage" in data:
                data["local_model_usage"] = data.pop("api_usage")
            if "api_preflight" in data:
                data["model_preflight"] = data.pop("api_preflight")
        original_save(path, data)

    experiment.save = save_with_backend_metadata
    sys.argv = [
        "run.py",
        "--model", MODEL_ID,
        "--worlds", os.getenv("SHAMAN_WORLDS", "12"),
        "--seed", os.getenv("SHAMAN_SEED", "20261105"),
        "--out", str(OUTPUT_DIR),
    ]
    experiment.main()

    summary = OUTPUT_DIR / "summary.md"
    if summary.exists():
        text = summary.read_text(encoding="utf-8")
        text = text.replace("## API usage", "## Local model usage")
        summary.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
