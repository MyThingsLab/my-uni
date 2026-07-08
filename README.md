# my-uni

[![CI](https://github.com/MyThingsLab/my-uni/actions/workflows/ci.yml/badge.svg)](https://github.com/MyThingsLab/my-uni/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/MyThingsLab/my-uni/branch/main/graph/badge.svg)](https://codecov.io/gh/MyThingsLab/my-uni)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)

A [MyThingsLab](../my-things-core) `My[X]` tool: given a "field of study" issue
(e.g. "Computer Science, undergrad-equivalent depth"), decomposes the field
into a curriculum — an ordered set of topics with prerequisites — and opens
each as its own issue labeled both `my-uni` and `my-researcher` so
**MyResearcher** picks it up on its own schedule and produces a cited study
brief for it.

MyUni is deliberately **upstream** of MyResearcher, not a duplicate: MyUni
decides what the topics of a field *are*; MyResearcher's `plan` mode orders
topics it's *given*. The two are coupled only through the issue tracker.

## Usage

```bash
# Decompose a field issue into up to 12 topic issues.
myuni plan --issue 7 --repo MyThingsLab/study --engine claude-cli

# Cap the curriculum size, dry-run against the noop engine:
myuni plan --issue 7 --max-topics 6 --engine noop
```

Each invocation makes **exactly one** Engine call. Against the default
`--engine noop` (zero tokens), the field issue's own title becomes the sole
topic — an honest degrade, never a fabricated curriculum. Re-running against
the same field issue extends the curriculum: already-opened topics are
deduped by title, never re-proposed.

MyUni never builds or ingests a knowledge corpus itself, and never calls
MyResearcher directly — it only opens issues MyResearcher already watches for.

## Install (development)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ../my-things-core -e ../my-guard -e ".[dev]"
pytest
```

See [`CLAUDE.md`](CLAUDE.md) for the tool's seams and [`HARNESS.md`](HARNESS.md)
for the inherited build rules.

## License

MIT — see [`LICENSE`](LICENSE).
