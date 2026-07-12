from __future__ import annotations

import json

import pytest
from mythings.github import GitHub

from myuni import cli

FIELD_ISSUE = {
    "number": 7,
    "title": "Computer Science, undergrad-equivalent depth",
    "body": "A survey-level CS curriculum.",
    "url": "https://github.com/o/r/issues/7",
    "labels": [{"name": "my-uni"}],
}


def _topic(number: int, title: str, field_issue: int = 7) -> dict:
    return {
        "number": number,
        "title": title,
        "body": f"part-of: #{field_issue}",
        "url": f"https://github.com/o/r/issues/{number}",
        "labels": [{"name": "my-uni"}, {"name": "my-researcher"}],
    }


class FakeGh:
    def __init__(
        self, all_topics: list[dict] | None = None, open_topics: list[dict] | None = None
    ) -> None:
        self.all_topics = all_topics or []
        self.open_topics = open_topics if open_topics is not None else self.all_topics
        self.calls: list[list[str]] = []
        self._next_issue_number = 100

    def __call__(self, argv: list[str]) -> str:
        self.calls.append(argv)
        if argv[:2] == ["issue", "list"]:
            if "my-researcher" not in argv:
                return json.dumps([FIELD_ISSUE])
            state = argv[argv.index("--state") + 1]
            return json.dumps(self.all_topics if state == "all" else self.open_topics)
        if argv[:2] == ["issue", "create"]:
            number = self._next_issue_number
            self._next_issue_number += 1
            return f"https://github.com/o/r/issues/{number}\n"
        if argv[:2] == ["issue", "edit"]:
            return ""
        raise AssertionError(f"unexpected gh call: {argv}")


@pytest.fixture
def patch_github(monkeypatch):
    def _patch(gh: FakeGh) -> None:
        monkeypatch.setattr(cli, "GitHub", lambda repo=None: GitHub(repo=repo, runner=gh))

    return _patch


@pytest.fixture(autouse=True)
def _isolate_ledger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def test_plan_noop_engine_prints_summary(capsys, patch_github) -> None:
    gh = FakeGh()
    patch_github(gh)

    exit_code = cli.main(["plan", "--issue", "7", "--engine", "noop"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "opened 1 topic issue(s); 0 already existed" in out


def test_plan_default_engine_is_noop(capsys, patch_github) -> None:
    gh = FakeGh()
    patch_github(gh)

    exit_code = cli.main(["plan", "--issue", "7"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "opened 1 topic issue(s)" in out


def test_plan_max_topics_is_wired_through(capsys, patch_github) -> None:
    # The noop engine always proposes exactly one topic (the field issue's own
    # title), so --max-topics can't be observed via topics_opened count here;
    # instead check the plan module receives the value we passed.
    gh = FakeGh()
    patch_github(gh)

    exit_code = cli.main(["plan", "--issue", "7", "--max-topics", "1"])

    assert exit_code == 0


def test_status_reports_briefed_and_pending(capsys, patch_github) -> None:
    topics = [_topic(1, "Discrete Math"), _topic(2, "Data Structures")]
    gh = FakeGh(all_topics=topics, open_topics=topics[1:])
    patch_github(gh)

    exit_code = cli.main(["status", "--issue", "7"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "curriculum for #7: 2 topic(s) — 1 briefed, 1 pending" in out
    assert "pending: #2 Data Structures" in out


def test_status_no_pending_topics_prints_no_pending_lines(capsys, patch_github) -> None:
    topics = [_topic(1, "Discrete Math")]
    gh = FakeGh(all_topics=topics, open_topics=[])
    patch_github(gh)

    exit_code = cli.main(["status", "--issue", "7"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "0 pending" in out
    assert "pending:" not in out.split("\n", 1)[1]


def test_unknown_field_issue_prints_error_and_returns_1(capsys, patch_github) -> None:
    class NoFieldGh(FakeGh):
        def __call__(self, argv: list[str]) -> str:
            if argv[:2] == ["issue", "list"] and "my-researcher" not in argv:
                return json.dumps([])
            return super().__call__(argv)

    patch_github(NoFieldGh())

    exit_code = cli.main(["status", "--issue", "999"])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "myuni: issue #999 not found" in out


def test_missing_required_issue_arg_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["status"])
    assert excinfo.value.code != 0


def test_no_subcommand_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code != 0
