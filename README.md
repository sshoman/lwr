# Agentic Learning Without Retention

This is a replication of the experiment from **Agentic Learning Without Retention: Turning Domain Experience into Transferable Understanding**.

The basic idea is pretty simple.

We keep trying to make generalist agents by giving them more memory. More examples, more context, more past experiences, more stuff to retrieve.

This experiment asks a different question:

**What happens when the agent learns from those experiences, turns them into principles, and then loses access to the original experiences?**

The paper's architecture is:

**Experience → Guess → Refutation → Principle → World Model → Forget**

The important part is that forgetting happens last. We are not deleting random memories and hoping intelligence appears. Shaman first looks across the experience, makes guesses about what is going on, tries to kill those guesses, and only lets the surviving structure become part of the persistent world model.

## The test

The experiment has four conditions.

1. **base**
   The base generalist gets no special reflective memory.

2. **summary**
   The same experience is compressed into an ordinary summary. This is the boring memory baseline we should beat if the full reflective process is actually doing something useful.

3. **reflective_retention**
   Shaman runs exactly the same reflection process as the forgetting condition, but the old experiences stay available.

4. **reflective_forgetting**
   Same Shaman work, same guesses, same refutations, same principles, same ranking, same world model. The only important difference is that the old experiences are removed from normal retrieval after the reflective stage.

The third and fourth conditions are the real experiment.

If reflective forgetting is useful, it should lose some exact recall while doing better on some unfamiliar transfer tasks. If it only ties retention, then forgetting did not add anything. If it beats retention only because retrieval became cleaner, then we probably built a retrieval trick rather than the learning process described in the paper.

## What is in the benchmark

The training curriculum is deliberately split between **coding** and **interface design**.

The domains look different, but some of the structures underneath them overlap: asynchronous state, retries, ownership, coupling, feedback, uncertainty, reversibility, friction, abstraction, and independent change.

The curriculum also contains counterexamples. A simple rule should get attacked by a case where the rule stops working.

That matters because the paper is not trying to reward the model for finding the same answer over and over. Shaman is supposed to get uncomfortable.

The evaluation then uses new surfaces that were not in the curriculum. There are also a few exact-recall questions on purpose. We want the experiment to show the trade-off instead of quietly defining success as “the thing that forgets wins.”

## Run it

For a real run, point it at any OpenAI-compatible chat-completions endpoint:

```bash
set OPENAI_API_KEY=your_key
python run_experiment.py --model your-model
```

You can also change the endpoint:

```bash
python run_experiment.py --base-url http://localhost:8000/v1 --model your-local-model
```

The experiment writes a full JSON result containing the experiences, guesses, every refutation, principles, world model, and scores for all four conditions.

A deterministic `--mock` mode exists, but only to smoke-test that the harness wiring works without an API key. It does not run the experiment.

## The result I actually care about

Do not look only at the final score.

The interesting result is the shape of the trade-off:

**less exact recall → less dependence on old episodes → more use of transferable principles → better unfamiliar transfer**

That is the thing this paper is actually claiming.

If the numbers do not show that, the experiment should make that obvious.

## One important limitation

The paper deliberately leaves the final real-world beta system unspecified. So this repo implements the **published experimental design**, using a reproducible synthetic transfer suite based on the curriculum and evaluation described in the paper. It is a replication harness, not a claim that this synthetic benchmark is the final proof of the idea.

The final beta described by the paper can be added as another evaluation suite without changing the four-condition logic.
