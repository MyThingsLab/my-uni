# my-uni — agent instructions

You are developing **my-uni**, a MyThingsLab My[X] tool.

**Inherited rules:** obey [`./HARNESS.md`](./HARNESS.md) in full — the vendored
MyThingsLab build-harness rules. Do not restate or override them. Anything not
covered here defers to `HARNESS.md`, then `mythings-core/docs/CONVENTIONS.md`.

## This tool

- **Purpose:** given a "field of study" issue, decomposes the field into a
  curriculum — an ordered set of topics with prerequisites — and opens each as
  its own issue labeled both `my-uni` and `my-researcher` so **MyResearcher**
  picks it up and produces a cited study brief for it. Deliberately upstream of
  MyResearcher, not a duplicate: MyUni decides what a field's topics *are*;
  MyResearcher's `plan` mode only orders topics it's *given*.
- **The single Engine call:** one per invocation — "decompose this field into
  a curriculum: an ordered list of topics, each with a one-line rationale and
  its prerequisites" → `{"topics": [{"title", "rationale", "prereqs"}]}`.
  Against `NoopEngine`, emits the field issue's own title as the sole topic —
  honest degrade, no decomposition.
- **Invariants / rules:** exactly one Engine call per run; post-Engine dedupe
  is deterministic — drop any proposed topic whose title case-insensitively
  matches an already-opened topic (matched via a `part-of: #N` marker in the
  topic issue body); deterministic truncation to `--max-topics` (default 12),
  never trusting the model's enthusiasm for how big a field is. Never calls
  MyResearcher directly — only opens issues MyResearcher already watches for.
  Never ingests a corpus itself. No `Workspace`, no PR — the only side effect
  is a series of `create_issue`/`add_labels` calls, each an
  `Action(kind="issue-create")` through `Policy.evaluate()`, `ALLOW` by
  default (low-risk, reversible — a human can close any of them).
- **Backlog label:** `my-uni`
