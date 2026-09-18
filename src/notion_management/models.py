from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class Comment:
    created_at: date
    text: str = ""
    mentioned_user_ids: tuple[str, ...] = ()
    mentioned_names: tuple[str, ...] = ()
    author_id: str = ""
    author_name: str = ""
    comment_id: str = ""
    created_at_time: datetime | None = None


@dataclass(frozen=True)
class Record:
    source: str
    page_id: str
    title: str
    status: str = ""
    owner: str = ""
    owner_id: str = ""
    approver_count: int = 0
    due_date: date | None = None
    updated_at: date | None = None
    priority: str = ""
    project_id: str = ""
    area: str = ""
    area_id: str = ""
    area_ids: tuple[str, ...] = ()
    request_team: str = ""
    kind: str = ""
    comments: tuple[Comment, ...] = ()
    approver_names: tuple[str, ...] = ()
    page_url: str = ""
    comment_recipient: str = ""
    template_missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    source: str
    page_id: str
    title: str
    rule: str
    message: str
    recipient: str = ""
    url: str = ""


def latest_comment(record: "Record") -> Comment | None:
    """Comentário mais recente, com desempate por timestamp, data e ordem original."""
    return max(
        enumerate(record.comments),
        key=lambda item: (
            item[1].created_at_time.timestamp() if item[1].created_at_time else 0,
            item[1].created_at.toordinal(),
            item[0],
        ),
        default=(0, None),
    )[1]


def has_comment_on(record: "Record", day: date) -> bool:
    return any(comment.created_at == day for comment in record.comments)


@dataclass
class AuditReport:
    records: list[Record] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    excluded_by_source: dict[str, int] = field(default_factory=dict)
    run_id: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    policy_version: str = "1"
    complete: bool = True
    source_results: dict[str, dict] = field(default_factory=dict)

    @property
    def counts_by_source(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for record in self.records:
            result[record.source] = result.get(record.source, 0) + 1
        return result
