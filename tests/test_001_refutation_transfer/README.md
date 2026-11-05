# Test 001: objective refutation and transfer

## Research question

Can an LLM turn observed outcomes into conditional claims, select tests intended to break those claims, survive an objective test runner, and help a new LLM context make better decisions on unseen task families after the source episodes are removed?

## Experimental loop

1. Generate 12 independently seeded hidden simulator worlds.
2. Each world provides 10 source incidents with five Boolean features and directly observed outcomes.
3. Gemini's Mechanism Generator proposes up to three structured conditional claims, or abstains.
4. A separate Gemini call acts as the Refutation Test Planner and selects four cases from a challenge pool. Candidate wording and predictions are frozen before execution.
5. A local deterministic simulator executes the tests. It does not ask an LLM to judge results.
6. A deterministic evaluator records support and contradiction and applies the promotion gates.
7. A four-test uniform-random selection arm receives the same candidate pool and budget.
8. A receiving LLM is evaluated on 12 unseen cases from three held-out task families under seven memory conditions. Three exact-recall probes measure what is lost when episodes are removed.
9. Only after model calls finish does the evaluator use the hidden rule to calculate full truth-table accuracy and false promotions.

## Memory conditions

- No memory.
- Original episodes.
- Ordinary summary.
- Unrefuted candidate claims.
- Candidates passing random tests.
- Shaman-tested World Model only.
- The same Shaman World Model plus source episodes, as a forgetting ablation.

## Promotion gate

A candidate is marked `transfer_tested` only if it has at least two independent supporting source incidents, at least three correct frozen predictions out of four, both prediction outcomes tested, two task families covered, and a boundary pair that flips one stated condition and changes the candidate prediction.

A passing claim is certified only inside this simulator. The certificate makes no real-world causal claim.

## Benchmark limits

The simulator has five Boolean features. Their meanings are randomly assigned to feature IDs in each world. Hidden rules are sampled from AND, OR, XOR, and feature-independent/no-stable-rule patterns. The claim language is restricted to one such Boolean expression over up to three literals. This makes objective execution possible but does not cover the full range of mechanisms Shaman may encounter.

The 12-world sample is a pilot. Confidence intervals resample worlds, not individual decisions. The same Gemini model fills isolated generator, planner, summary and recipient roles, so model errors may be correlated.

## Run

The root PowerShell command downloads the repository, extracts this test's source bundle, prompts for the Gemini API key without echoing it, and runs the experiment. The client uses the Gemini Developer API's native `generateContent` endpoint and sends the credential in the `x-goog-api-key` header. No third-party Python packages are required.
