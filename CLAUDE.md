# my-uni — agent instructions

You are developing **my-uni**, a MyThingsLab My[X] tool.

**Inherited rules:** obey [`./HARNESS.md`](./HARNESS.md) in full — the vendored
MyThingsLab build-harness rules. Do not restate or override them. Anything not
covered here defers to `HARNESS.md`, then `mythings-core/docs/CONVENTIONS.md`.

## This tool

- **Purpose:** given a "field of study" issue (label `my-uni`), decompose the
  field into a curriculum — an ordered set of topics with prerequisites — and
  open each topic as its own issue labeled both `my-uni` and `my-researcher`
  so MyResearcher picks it up on its own schedule.
- **The single Engine call:** "decompose this field into a curriculum: an
  ordered list of topics, each with a one-line rationale and its
  prerequisites." Input is the field issue's title + body plus the titles of
  topics already opened for it (so a re-run extends rather than re-proposes).
  Against `NoopEngine` (or any engine giving no usable reply): the field
  issue's own title becomes the sole topic — never a fabricated curriculum.
- **Invariants:** exactly one Engine call per run; post-Engine dedupe drops
  any proposed topic whose title case-insensitively matches an already-opened
  one; the survivors are truncated to `--max-topics` (default 12) —
  deterministic, not model-driven. MyUni never builds or ingests a knowledge
  corpus, and never calls MyResearcher directly — it only opens issues
  MyResearcher already watches for.
- **Backlog label:** `my-uni`.
