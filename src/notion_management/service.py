from dataclasses import replace
from datetime import date, datetime
from typing import Any

from .config import Settings
from .models import AuditReport, Comment, Record
from .notion_api import NotionClient
from .quality import audit
from .scope import in_scope
from .template import missing_sections


REPORT_TASK_STATUSES = {"Em Progresso", "Bloqueada", "Para ser aprovada"}
REPORT_PROJECT_STATUSES = {"Doing", "Blocked", "TBA", "Em Progresso", "Bloqueada", "Para ser aprovada"}
REPORT_COLTEC_COMPLETED_STATUSES = {"Feito", "Done", "Concluído", "Concluída"}
REPORT_REQUEST_STATUSES = {"Inbox", "Formatada", "Atendimento BBTS", "Atendimento Core", "On hold", "Comunicar cliente", "Comunicado e aguardando feedback", "Solicitação bloqueada"}


def _text(properties: dict[str, Any], name: str) -> str:
    prop = properties.get(name, {})
    values = prop.get("title", []) or prop.get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in values).strip()


def _option(properties: dict[str, Any], name: str) -> str:
    prop = properties.get(name, {})
    value = prop.get("select") or prop.get("status")
    return (value or {}).get("name", "")


def _person(properties: dict[str, Any], name: str) -> str:
    people = properties.get(name, {}).get("people", [])
    return (people[0].get("name") or people[0].get("id", "")) if people else ""


def _person_id(properties: dict[str, Any], name: str) -> str:
    people = properties.get(name, {}).get("people", [])
    return people[0].get("id", "") if people else ""


def _people_count(properties: dict[str, Any], name: str) -> int:
    return len(properties.get(name, {}).get("people", []))


def _people_names(properties: dict[str, Any], name: str) -> tuple[str, ...]:
    return tuple(person.get("name") or person.get("id", "") for person in properties.get(name, {}).get("people", []))


def _comments(raw_comments: list[dict[str, Any]]) -> tuple[Comment, ...]:
    result: list[Comment] = []
    for raw in raw_comments:
        created = raw.get("created_time")
        if not created:
            continue
        author = raw.get("created_by") or {}
        text_parts: list[str] = []
        user_ids: list[str] = []
        names: list[str] = []
        for item in raw.get("rich_text", []):
            text_parts.append(item.get("plain_text", ""))
            mention = item.get("mention", {})
            user = mention.get("user", {}) if mention.get("type") == "user" else {}
            if user.get("id"):
                user_ids.append(user["id"])
                names.append(user.get("name") or user["id"])
        result.append(Comment(
            created_at=datetime.fromisoformat(created.replace("Z", "+00:00")).date(),
            text="".join(text_parts).strip(),
            mentioned_user_ids=tuple(user_ids),
            mentioned_names=tuple(names),
            author_id=author.get("id", ""),
            author_name=author.get("name") or author.get("id", "") or "Autor não identificado",
        ))
    return tuple(sorted(result, key=lambda comment: comment.created_at))


def _last_team_mention(comments: tuple[Comment, ...], member_ids: tuple[str, ...]) -> str:
    members = {item.replace("-", "").lower() for item in member_ids}
    for comment in reversed(comments):
        for user_id, name in reversed(tuple(zip(comment.mentioned_user_ids, comment.mentioned_names))):
            if user_id.replace("-", "").lower() in members:
                return name
    return ""


def _date(properties: dict[str, Any], name: str) -> date | None:
    value = (properties.get(name, {}).get("date") or {}).get("start")
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _system_date(properties: dict[str, Any], name: str) -> date | None:
    prop = properties.get(name, {})
    value = prop.get("last_edited_time") or prop.get("created_time")
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _relation(properties: dict[str, Any], name: str) -> str:
    values = properties.get(name, {}).get("relation", [])
    return values[0].get("id", "") if values else ""


def _relation_ids(properties: dict[str, Any], name: str) -> tuple[str, ...]:
    values = properties.get(name, {}).get("relation", [])
    return tuple(value.get("id", "") for value in values if value.get("id"))


def _normalize(source: str, page: dict[str, Any], status_name: str, owner_name: str, due_name: str, project_name: str = "") -> Record:
    props = page.get("properties", {})
    return Record(
        source=source,
        page_id=page.get("id", ""),
        title=_text(props, next((key for key, value in props.items() if value.get("type") == "title"), "")),
        status=_option(props, status_name),
        owner=_person(props, owner_name),
        owner_id=_person_id(props, owner_name),
        approver_count=_people_count(props, "Aprovadora"),
        due_date=_date(props, due_name),
        updated_at=_system_date(props, "Última atualização") or _system_date(props, " Ultima Edição") or (
            datetime.fromisoformat(page["last_edited_time"].replace("Z", "+00:00")).date()
            if page.get("last_edited_time") else None
        ),
        priority=_option(props, "Prioridade"),
        project_id=_relation(props, project_name) if project_name else "",
        area=_option(props, "Área"),
        area_id=_relation(props, "Área"),
        area_ids=_relation_ids(props, "Área"),
        request_team=_option(props, "Time Responsável"),
        kind=_option(props, "Tipo"),
        approver_names=_people_names(props, "Aprovadora"),
        page_url=f"https://www.notion.so/{page.get('id', '').replace('-', '')}" if page.get("id") else "",
    )


def run_audit(settings: Settings, today: date | None = None) -> AuditReport:
    settings.require_notion_token()
    client = NotionClient(settings.notion_token, settings.notion_version)
    records: list[Record] = []
    excluded_by_source: dict[str, int] = {}
    for source, data_source_id, status, owner, due, project in [
        ("tasks", settings.tasks_id, "Status", "Responsável", "Prazo", "Projeto"),
        ("projects", settings.projects_id, "Status", "Responsável", "Prazo", ""),
        ("coltec", settings.coltec_id, "Status", "Responsável", "Prazo", ""),
        ("requests", settings.requests_id, "Status da solicitação", "Quem atende", "Prazo prometido ao cliente", "Projeto Tech"),
    ]:
        for row in client.query_data_source(data_source_id):
            record = _normalize(source, row, status, owner, due, project)
            report_statuses = REPORT_TASK_STATUSES if source == "tasks" else REPORT_PROJECT_STATUSES
            if in_scope(record, settings):
                should_read_comments = (
                    source in {"tasks", "projects"} and record.status in report_statuses
                ) or (
                    source == "coltec" and record.status not in REPORT_COLTEC_COMPLETED_STATUSES
                ) or (
                    source == "requests" and record.status in REPORT_REQUEST_STATUSES
                )
                if should_read_comments:
                    comments = _comments(client.list_comments(record.page_id))
                    record = replace(record, comments=comments, comment_recipient=_last_team_mention(comments, settings.team_member_ids + (settings.manager_id,)))
                if source in {"tasks", "projects"} and record.status not in {"Feito", "Done", "Concluído", "Concluída"}:
                    blocks = client.list_block_children(record.page_id) if row.get("has_children") else []
                    record = replace(record, template_missing=missing_sections(source, row.get("properties", {}), blocks))
                records.append(record)
            else:
                excluded_by_source[source] = excluded_by_source.get(source, 0) + 1
    report = audit(records, today=today)
    report.excluded_by_source = excluded_by_source
    return report


def render_markdown(report: AuditReport) -> str:
    lines = ["*Resumo de gestão — Equipe de Integrações*", ""]
    lines.append(" | ".join(f"{source}: {count}" for source, count in sorted(report.counts_by_source.items())))
    if report.excluded_by_source:
        ignored = " | ".join(f"{source}: {count}" for source, count in sorted(report.excluded_by_source.items()))
        lines.append(f"Ignorados por escopo: {ignored}")
    lines.append(f"Achados prioritários: {len(report.findings)}")
    for finding in report.findings[:20]:
        lines.append(f"- [{finding.rule}] {finding.title}: {finding.message}")
    if len(report.findings) > 20:
        lines.append(f"- ... e mais {len(report.findings) - 20} achados no relatório detalhado.")
    return "\n".join(lines)
