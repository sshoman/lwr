# Shaman experiments

This repository contains research tests only. It is not the CI 1on1 application and it is not a product runtime.

Every experiment lives in its own directory under `tests/`. Each directory owns its benchmark, prompts, runner, scoring rules, and report format. Shared infrastructure belongs in `tests/shared/` only when two completed experiments genuinely need the same code.

## Test 001: independent refutation and transfer

`tests/test_001_refutation_transfer/` is the first LLM-backed pilot of Shaman's central claim.

The experiment creates independent hidden simulator worlds. Gemini receives observed experiences, proposes up to three conditional claims, and chooses four challenge cases intended to break those claims. The test runner executes those cases against the simulator. It does not ask Gemini to judge its own answers. The evaluator compares frozen predictions with the simulator's actual outcomes and writes evidence certificates.

A separate receiving context gets one of several memory conditions and makes decisions on unseen cases from new task families. Gold outcomes are withheld from every model prompt and used only by the local evaluator.

Memory conditions:

1. No memory.
2. Original episodes.
3. Ordinary summary.
4. Unrefuted candidate claims.
5. Claims that passed randomly selected tests.
6. Claims that passed Shaman's adversarially selected tests, without source episodes.
7. The same Shaman model with source episodes retained, as the forgetting ablation.

The first run is a pilot across 12 independently seeded worlds. It is useful for finding failures in the method, not enough to establish a broad research claim. The report includes per-world results, confidence intervals, rejected claims, invalid test plans, model usage, and the sealed simulator truth. Do not quote aggregate results without the limitations in the report.

## Run Test 001

Test 001 now runs automatically in GitHub Actions when the experiment workflow is added or the experiment files change on `main`. It does not run on your Windows machine and does not require a Gemini API key.

The automated replication rebuilds and verifies the seven source chunks, then runs the original experiment runner against a local Qwen3-4B Q4_K_M model served by llama.cpp on a GitHub-hosted Ubuntu runner. Results are uploaded as a workflow artifact and the summary is added to the workflow page.

This is a different model from the original Gemini 3.8 plan. It tests the same simulator, claim generation, refutation selection, memory conditions, and deterministic evaluator, but its results must be labelled as the Qwen3 local-model replication and must not be pooled with Gemini results.

## What Test 001 can and cannot show

It can test whether an LLM can infer a conditional mechanism from observed outcomes, propose tests intended to distinguish competing explanations, survive objective simulator checks, and pass useful knowledge to a new LLM context without the source episodes.

It cannot establish that Shaman works across arbitrary real-world agents or domains. The first benchmark uses a controlled synthetic environment with a deliberately limited claim language. Its purpose is to test the core loop without letting the model grade itself. A later experiment must use real coding and design tasks, independent task evaluators, and a larger preregistered sample.

## Repository rules

- One experiment per `tests/test_NNN_name/` directory.
- Keep benchmark truth separate from model-visible prompts.
- Register candidate versions and predictions before executing a test.
- Test runners return raw observations; evaluators do not rewrite them.
- Invalid tests count as neither support nor refutation.
- Never use model-written confidence or self-assigned quality scores as promotion evidence.
- Never commit API keys, local results, or environment files.
