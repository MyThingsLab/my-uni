from __future__ import annotations

from dataclasses import dataclass

from mythings.github import GitHub, Issue
from mythings.ledger import Ledger

from myuni.plan import TOPIC_LABELS, _find_field_issue, _part_of_marker


@dataclass(frozen=True)
class TopicStatus:
    number: int
    title: str
    briefed: bool  # closed == a merged research PR ("Closes #n") resolved it


@dataclass(frozen=True)
class StatusResult:
    field_issue: int
    topics: list[TopicStatus]

    @property
    def briefed(self) -> list[TopicStatus]:
        return [t for t in self.topics if t.briefed]

    @property
    def pending(self) -> list[TopicStatus]:
        return [t for t in self.topics if not t.briefed]


def _curriculum_topics(github: GitHub, field_issue: int, state: str) -> list[Issue]:
    marker = _part_of_marker(field_issue)
    topics = github.list_issues(labels=TOPIC_LABELS, state=state, limit=100)
    return [issue for issue in topics if marker in issue.body]


def status(*, issue: int, github: GitHub, ledger: Ledger) -> StatusResult:
    field_issue = _find_field_issue(github, issue)

    # Issue carries no state, so derive it: a curriculum topic absent from the
    # open set is closed — i.e. its cited brief landed and resolved it.
    all_topics = _curriculum_topics(github, field_issue.number, "all")
    open_numbers = {t.number for t in _curriculum_topics(github, field_issue.number, "open")}
    topics = [
        TopicStatus(number=t.number, title=t.title, briefed=t.number not in open_numbers)
        for t in sorted(all_topics, key=lambda t: t.number)
    ]

    result = StatusResult(field_issue=field_issue.number, topics=topics)
    ledger.record(
        "myuni",
        "coverage",
        "success",
        detail=(
            f"coverage for #{issue} "
            f"({len(result.briefed)}/{len(topics)} topics briefed)"
        ),
        field_issue=issue,
        topics_briefed=[t.number for t in result.briefed],
        topics_pending=[t.number for t in result.pending],
    )
    return result
