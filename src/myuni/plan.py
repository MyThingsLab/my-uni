from __future__ import annotations

import json
from dataclasses import dataclass, field

from mythings.engine import Engine, EngineRequest
from mythings.github import GitHub, Issue
from mythings.ledger import Ledger
from mythings.policy import Action, Decision, Policy

FIELD_LABEL = "my-uni"
TOPIC_LABELS = ["my-uni", "my-researcher"]
DEFAULT_MAX_TOPICS = 12

_SYSTEM = (
    "You decompose a field of study into a curriculum. Reply with only a JSON "
    'object of the shape {"topics": [{"title": str, "rationale": str, '
    '"prereqs": [str, ...]}, ...]}. A prereq may only name a title that also '
    "appears in this same topics list. No prose, no markdown fences — JSON only."
)


@dataclass(frozen=True)
class Topic:
    title: str
    rationale: str = ""
    prereqs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlanResult:
    field_issue: int
    topics_opened: list[int]
    topics_deduped: list[str]


def _part_of_marker(field_issue: int) -> str:
    return f"part-of: #{field_issue}"


def _find_field_issue(github: GitHub, number: int) -> Issue:
    for issue in github.list_issues(labels=[FIELD_LABEL], state="all", limit=100):
        if issue.number == number:
            return issue
    raise ValueError(f"issue #{number} not found under the '{FIELD_LABEL}' label")


def _existing_topic_titles(github: GitHub, field_issue: int) -> list[str]:
    marker = _part_of_marker(field_issue)
    topics = github.list_issues(labels=TOPIC_LABELS, state="all", limit=100)
    return [issue.title for issue in topics if marker in issue.body]


def _propose_topics(engine: Engine, field_issue: Issue, existing_titles: list[str]) -> list[Topic]:
    prompt = f"Field issue #{field_issue.number}: {field_issue.title}\n\n{field_issue.body}"
    context = {"field_issue": field_issue.number, "existing_topics": existing_titles}
    result = engine.run(EngineRequest(prompt=prompt, system=_SYSTEM, context=context))
    try:
        payload = json.loads(result.text) if result.text else {}
    except json.JSONDecodeError:
        payload = {}
    raw_topics = payload.get("topics")
    if not raw_topics:
        # Honest degrade (NoopEngine, or any engine that gave no usable reply):
        # the field issue's own title becomes the sole topic, never a
        # fabricated curriculum.
        return [Topic(title=field_issue.title)]
    return [
        Topic(
            title=str(t["title"]),
            rationale=str(t.get("rationale", "")),
            prereqs=[str(p) for p in t.get("prereqs", [])],
        )
        for t in raw_topics
    ]


def _dedupe(topics: list[Topic], existing_titles: list[str]) -> tuple[list[Topic], list[str]]:
    existing_lower = {title.lower() for title in existing_titles}
    survivors: list[Topic] = []
    deduped: list[str] = []
    for topic in topics:
        if topic.title.lower() in existing_lower:
            deduped.append(topic.title)
        else:
            survivors.append(topic)
    return survivors, deduped


def _topic_body(topic: Topic, field_issue: int) -> str:
    lines: list[str] = []
    if topic.rationale:
        lines += [topic.rationale, ""]
    if topic.prereqs:
        lines += ["Prerequisites: " + ", ".join(topic.prereqs), ""]
    lines.append(_part_of_marker(field_issue))
    return "\n".join(lines)


def plan(
    *,
    issue: int,
    engine: Engine,
    github: GitHub,
    policy: Policy,
    ledger: Ledger,
    max_topics: int = DEFAULT_MAX_TOPICS,
) -> PlanResult:
    field_issue = _find_field_issue(github, issue)
    existing_titles = _existing_topic_titles(github, issue)

    proposed = _propose_topics(engine, field_issue, existing_titles)
    survivors, deduped = _dedupe(proposed, existing_titles)
    survivors = survivors[:max_topics]  # deterministic truncation, not a model-driven cap

    opened: list[int] = []
    for topic in survivors:
        action = Action(kind="issue-create", payload={"title": topic.title, "field_issue": issue})
        if policy.evaluate(action).under(unattended=True) is not Decision.ALLOW:
            continue
        created = github.create_issue(title=topic.title, body=_topic_body(topic, issue))
        github.add_labels(created.number, TOPIC_LABELS)
        opened.append(created.number)

    ledger.record(
        "myuni",
        "curriculum",
        "success",
        detail=f"curriculum for #{issue} ({len(opened)} new, {len(deduped)} already open)",
        field_issue=issue,
        topics_opened=opened,
        topics_deduped=deduped,
    )
    return PlanResult(field_issue=issue, topics_opened=opened, topics_deduped=deduped)
