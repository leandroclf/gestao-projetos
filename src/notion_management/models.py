from dataclasses import dataclass, field
from datetime import date


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
    request_team: str = ""
    kind: str = ""


@dataclass(frozen=True)
class Finding:
    source: str
    page_id: str
    title: str
    rule: str
    message: str


@dataclass
class AuditReport:
    records: list[Record] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    excluded_by_source: dict[str, int] = field(default_factory=dict)

    @property
    def counts_by_source(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for record in self.records:
            result[record.source] = result.get(record.source, 0) + 1
        return result
