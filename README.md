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

## Run from Windows PowerShell

Use this one command from any folder:

```powershell
irm https://raw.githubusercontent.com/sshoman/lwr/main/run.ps1 | iex
```

The script downloads the current repository to a temporary folder, checks for Python 3.10+, and starts Test 001. The Python runner asks for the Gemini API key using a hidden prompt if `GEMINI_API_KEY` is not already set. The key is not saved to disk or printed. Results are written to `shaman-results/` in the folder where the command was run.

No pip packages are needed. The runner uses Python's standard library.

Defaults: `gemini-3.8-flash`, 12 worlds, 12 held-out transfer decisions per world, four Shaman-selected challenge cases per world, and four random challenge cases per world. The run records token usage, rejected claims, and false promotions. A run stops early if the API reports quota or authentication failure. Partial records are saved as it proceeds.

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
