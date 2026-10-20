# Formal P1 offline verification

Run from the repository root:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v22/17_p1_input/offline/capacity.py
```

Run the codec tests from `experiments/methods/v22/17_p1_input/revision`:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -m unittest tests.skill_evolution.v22.test_p1_input -v
```

`capacity.py` imports the archived seed loader and synthetic fixture generator from
16. It uses the **formal v4** `grouped_messages` / `grouping_messages` paths, their
actual P1 instructions and `p1_input` codec. It never calls the prototype encoder,
the old generator's writer, a model API, or an environment.

The first five rows project the same archived 08 R2 facts under v3 and v4 rules.
They are counterfactual input measurements, not historical v3/v4 model calls.
For learning, the previously saved Editor mapping is attached and the view binding
is recomputed in memory, never on a checkpoint. The remaining 200 rows are explicitly
synthetic storage-shaped scenarios. Their cloned task/group/outcome structures are
not valid new episodes and do not establish behavior, classification or causality.

All comparisons assert decoded data equality, after the declared profile identity
and derived learning-binding change, and equality of the System rules except the
profile label and P1 decoding instruction. Every scenario records its digest,
source/event counts, size and local encode/decode timing.

Token ranges are an uncalibrated **2–4 message-content characters per token**
sensitivity range. They are neither actual provider usage nor a tokenizer count.
Read the later frozen live probes for actual input/completion/reasoning Tokens.

No lossy Editor view, history cards, evidence selection or truncation is used.
Over-limit inputs remain over limit and are reported. The codec's literal fallback
preserves legal metadata containing reserved encoding keys without blocking an
otherwise valid update; those rare inputs need not achieve compression.

Results: `artifacts/methods/v22/17_p1_input/offline/capacity_results.json` and
`codec_tests.log`. Full V22 and Adapter regression logs are maintained separately by
the profile integration verification.
