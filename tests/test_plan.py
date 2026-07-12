from __future__ import annotations

import json

from mythings.engine import EngineRequest, EngineResult
from mythings.github import GitHub
from mythings.ledger import Ledger
from mythings.policy import Action, Decision, Policy, PolicyResult
from mythings.testing import ScriptedEngine

from myuni.plan import plan

FIELD_ISSUE = {
    "number": 7,
    "title": "Computer Science, undergrad-equivalent depth",
    "body": "A survey-level CS curriculum.",
    "url": "https://github.com/o/r/issues/7",
    "labels": [{"name": "my-uni"}],
}


class FakeGh:
    def __init__(self, existing_topics: list[dict] | None = None) -> None:
        self.existing_topics = existing_topics or []
        self.calls: list[list[str]] = []
        self._next_issue_number = 100

    def __call__(self, argv: list[str]) -> str:
        self.calls.append(argv)
        if argv[:2] == ["issue", "list"]:
            if "my-researcher" in argv:
                return json.dumps(self.existing_topics)
            return json.dumps([FIELD_ISSUE])
        if argv[:2] == ["issue", "create"]:
            number = self._next_issue_number
            self._next_issue_number += 1
            return f"https://github.com/o/r/issues/{number}\n"
        if argv[:2] == ["issue", "edit"]:
            return ""
        raise AssertionError(f"unexpected gh call: {argv}")


def scripted_topics(topics: list[dict]) -> ScriptedEngine:
    return ScriptedEngine(json.dumps({"topics": topics}))





class AllowAll:
    def evaluate(self, action: Action) -> PolicyResult:
        return PolicyResult(Decision.ALLOW)


def _topic_body_of(existing: dict) -> str:
    return existing["body"]


def _existing(number: int, title: str, field_issue: int) -> dict:
    return {
        "number": number,
        "title": title,
        "body": f"part-of: #{field_issue}",
        "url": f"https://github.com/o/r/issues/{number}",
        "labels": [{"name": "my-uni"}, {"name": "my-researcher"}],
    }


def _run(gh: FakeGh, engine: ScriptedEngine, *, max_topics: int = 12, policy: Policy | None = None):
    ledger = Ledger("/tmp/myuni-test-ledger.jsonl")
    return plan(
        issue=7,
        engine=engine,
        github=GitHub(runner=gh),
        policy=policy or AllowAll(),
        ledger=ledger,
        max_topics=max_topics,
    )


def test_happy_path_opens_new_topic_issues() -> None:
    proposed = [
        {"title": "Discrete Math", "rationale": "foundations", "prereqs": []},
        {"title": "Data Structures", "rationale": "core", "prereqs": ["Discrete Math"]},
        {"title": "Algorithms", "rationale": "core", "prereqs": ["Data Structures"]},
        {"title": "Operating Systems", "rationale": "systems", "prereqs": []},
        {"title": "Networking", "rationale": "systems", "prereqs": ["Operating Systems"]},
    ]
    gh = FakeGh(existing_topics=[])
    engine = scripted_topics(proposed)

    result = _run(gh, engine)

    assert len(result.topics_opened) == 5
    assert result.topics_deduped == []
    create_calls = [c for c in gh.calls if c[:2] == ["issue", "create"]]
    edit_calls = [c for c in gh.calls if c[:2] == ["issue", "edit"]]
    assert len(create_calls) == 5
    assert len(edit_calls) == 5
    for call in create_calls:
        body = call[call.index("--body") + 1]
        assert "part-of: #7" in body
    for call in edit_calls:
        assert "my-uni" in call and "my-researcher" in call
    assert len(engine.calls) == 1


def test_noop_degrade_uses_field_issue_title_as_sole_topic() -> None:
    gh = FakeGh(existing_topics=[])

    class Noop:
        def run(self, request: EngineRequest) -> EngineResult:
            return EngineResult(text="")

    result = _run(gh, Noop())

    assert len(result.topics_opened) == 1
    create_calls = [c for c in gh.calls if c[:2] == ["issue", "create"]]
    assert create_calls[0][create_calls[0].index("--title") + 1] == FIELD_ISSUE["title"]


def test_all_topics_already_exist_opens_nothing() -> None:
    proposed = [
        {"title": "Discrete Math", "rationale": "", "prereqs": []},
        {"title": "Data Structures", "rationale": "", "prereqs": []},
    ]
    existing = [_existing(1, "Discrete Math", 7), _existing(2, "Data Structures", 7)]
    gh = FakeGh(existing_topics=existing)
    engine = scripted_topics(proposed)

    result = _run(gh, engine)

    assert result.topics_opened == []
    assert sorted(result.topics_deduped) == ["Data Structures", "Discrete Math"]
    assert not [c for c in gh.calls if c[:2] == ["issue", "create"]]


def test_cap_exceeded_truncates_deterministically() -> None:
    proposed = [{"title": f"Topic {i}", "rationale": "", "prereqs": []} for i in range(20)]
    gh = FakeGh(existing_topics=[])
    engine = scripted_topics(proposed)

    result = _run(gh, engine, max_topics=3)

    assert len(result.topics_opened) == 3


def test_policy_deny_skips_creating_that_issue() -> None:
    proposed = [{"title": "Discrete Math", "rationale": "", "prereqs": []}]
    gh = FakeGh(existing_topics=[])
    engine = scripted_topics(proposed)

    class DenyAll:
        def evaluate(self, action: Action) -> PolicyResult:
            return PolicyResult(Decision.DENY)

    result = _run(gh, engine, policy=DenyAll())

    assert result.topics_opened == []
    assert not [c for c in gh.calls if c[:2] == ["issue", "create"]]
