from __future__ import annotations

import json

import pytest
from mythings.github import GitHub
from mythings.ledger import Ledger

from myuni.status import status

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
    def __init__(self, all_topics: list[dict], open_topics: list[dict]) -> None:
        self.all_topics = all_topics
        self.open_topics = open_topics
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> str:
        self.calls.append(argv)
        if argv[:2] == ["issue", "list"]:
            if "my-researcher" not in argv:
                return json.dumps([FIELD_ISSUE])
            state = argv[argv.index("--state") + 1]
            return json.dumps(self.all_topics if state == "all" else self.open_topics)
        raise AssertionError(f"unexpected gh call: {argv}")


def _run(gh: FakeGh, tmp_path):
    return status(issue=7, github=GitHub(runner=gh), ledger=Ledger(tmp_path / "ledger.jsonl"))


def test_closed_topics_count_as_briefed(tmp_path) -> None:
    topics = [_topic(1, "Discrete Math"), _topic(2, "Data Structures"), _topic(3, "Algorithms")]
    gh = FakeGh(all_topics=topics, open_topics=topics[1:])

    result = _run(gh, tmp_path)

    assert result.field_issue == 7
    assert [t.title for t in result.briefed] == ["Discrete Math"]
    assert [t.title for t in result.pending] == ["Data Structures", "Algorithms"]
    assert not [c for c in gh.calls if c[0] != "issue"]  # read-only: no side effects


def test_other_fields_topics_are_excluded(tmp_path) -> None:
    mine = _topic(1, "Discrete Math")
    other = _topic(2, "Thermodynamics", field_issue=9)
    gh = FakeGh(all_topics=[mine, other], open_topics=[mine, other])

    result = _run(gh, tmp_path)

    assert [t.title for t in result.topics] == ["Discrete Math"]


def test_empty_curriculum_reports_zero_topics(tmp_path) -> None:
    gh = FakeGh(all_topics=[], open_topics=[])

    result = _run(gh, tmp_path)

    assert result.topics == []
    assert result.briefed == []
    assert result.pending == []


def test_unknown_field_issue_raises(tmp_path) -> None:
    class NoField(FakeGh):
        def __call__(self, argv: list[str]) -> str:
            if argv[:2] == ["issue", "list"] and "my-researcher" not in argv:
                return json.dumps([])
            return super().__call__(argv)

    with pytest.raises(ValueError, match="not found"):
        _run(NoField(all_topics=[], open_topics=[]), tmp_path)
