#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lwr.client import LLMClient, LLMConfig
from lwr.experiment import LWRExperiment, save_result


def main() -> None:
    p = argparse.ArgumentParser(description="Run the Agentic Learning Without Retention experiment.")
    p.add_argument("--data", default="data")
    p.add_argument("--out", default="results/latest.json")
    p.add_argument("--model", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--max-guesses", type=int, default=6)
    p.add_argument("--refutations-per-guess", type=int, default=4)
    p.add_argument("--top-k", type=int, default=6)
    args = p.parse_args()

    config = LLMConfig(
        model=args.model or __import__("os").getenv("LWR_MODEL", "gpt-4o-mini"),
        base_url=args.base_url or __import__("os").getenv("LWR_BASE_URL", "https://api.openai.com/v1"),
        api_key=__import__("os").getenv("OPENAI_API_KEY"),
    )
    client = LLMClient(config=config)
    exp = LWRExperiment(args.data, client, args.max_guesses, args.refutations_per_guess, args.top_k)
    result = exp.run()
    save_result(result, args.out)

    print(f"Saved {args.out}")
    for name, row in result["results"].items():
        print(
            f"{name:24} overall={row['score']:.3f} "
            f"transfer={row['transfer_score']:.3f} "
            f"recall={row['exact_recall_score']:.3f} "
            f"episodes={row['memory_items_available']}"
        )


if __name__ == "__main__":
    main()
