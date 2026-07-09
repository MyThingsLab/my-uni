from __future__ import annotations

import argparse
from pathlib import Path

from myguard import Guard
from mythings.engine import ClaudeCLIEngine, Engine, NoopEngine
from mythings.github import GitHub
from mythings.ledger import Ledger

from myuni.plan import DEFAULT_MAX_TOPICS, plan
from myuni.status import status

_ENGINES: dict[str, type[Engine]] = {"noop": NoopEngine, "claude-cli": ClaudeCLIEngine}
_LEDGER_PATH = Path(".mythings") / "ledger.jsonl"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="myuni")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="decompose a field issue into curriculum topic issues")
    p.add_argument("--issue", type=int, required=True)
    p.add_argument("--repo", default=None, help="owner/name; defaults to the current repo")
    p.add_argument("--engine", choices=sorted(_ENGINES), default="noop")
    p.add_argument("--max-topics", type=int, default=DEFAULT_MAX_TOPICS)

    s = sub.add_parser("status", help="report a field's curriculum coverage (briefed vs pending)")
    s.add_argument("--issue", type=int, required=True)
    s.add_argument("--repo", default=None, help="owner/name; defaults to the current repo")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        if args.cmd == "plan":
            result = plan(
                issue=args.issue,
                engine=_ENGINES[args.engine](),
                github=GitHub(repo=args.repo),
                policy=Guard(),
                ledger=Ledger(_LEDGER_PATH),
                max_topics=args.max_topics,
            )
            print(
                f"opened {len(result.topics_opened)} topic issue(s); "
                f"{len(result.topics_deduped)} already existed"
            )
        elif args.cmd == "status":
            coverage = status(
                issue=args.issue,
                github=GitHub(repo=args.repo),
                ledger=Ledger(_LEDGER_PATH),
            )
            print(
                f"curriculum for #{coverage.field_issue}: {len(coverage.topics)} topic(s) — "
                f"{len(coverage.briefed)} briefed, {len(coverage.pending)} pending"
            )
            for topic in coverage.pending:
                print(f"  pending: #{topic.number} {topic.title}")
        else:
            return 1
    except ValueError as exc:
        print(f"myuni: {exc}", flush=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
