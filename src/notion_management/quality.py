from datetime import date, timedelta

from .models import AuditReport, Finding, Record


TASK_REVIEW_STATUSES = {"Em Progresso", "Bloqueada", "Para ser aprovada", "Feito"}
ACTIVE_PROJECT_STATUSES = {"Inbox", "Backlog", "Ready", "Doing", "Blocked", "TBA"}
ACTIVE_REQUEST_STATUSES = {"Inbox", "Formatada", "Atendimento BBTS", "Atendimento Core", "On hold", "Comunicar cliente", "Comunicado e aguardando feedback", "Solicitação bloqueada"}


def _business_day(day: date) -> date:
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def _business_days_since(start: date, end: date) -> int:
    start = _business_day(start)
    end = _business_day(end)
    if start >= end:
        return 0
    elapsed = 0
    cursor = start
    while cursor < end:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            elapsed += 1
    return elapsed


def audit(records: list[Record], today: date | None = None) -> AuditReport:
    today = today or date.today()
    findings: list[Finding] = []
    for record in records:
        if record.source == "requests" and record.status in ACTIVE_REQUEST_STATUSES and record.priority == "P0" and not record.project_id:
            findings.append(Finding(record.source, record.page_id, record.title, "urgent_without_project", "Solicitação P0 sem projeto técnico relacionado."))
        if record.source != "tasks" or record.status not in TASK_REVIEW_STATUSES:
            continue
        if not record.owner:
            findings.append(Finding(record.source, record.page_id, record.title, "owner_missing", "Tarefa em status controlado sem responsável."))
        if not record.due_date:
            findings.append(Finding(record.source, record.page_id, record.title, "due_date_missing", "Tarefa em status controlado sem prazo."))
        if record.status == "Para ser aprovada" and record.approver_count < 1:
            findings.append(Finding(record.source, record.page_id, record.title, "approver_missing", "Tarefa aguardando aprovação sem pelo menos um aprovador."))
        if record.due_date and record.due_date < today and record.status != "Feito":
            findings.append(Finding(record.source, record.page_id, record.title, "overdue", "Prazo vencido para tarefa ainda não concluída."))
        if record.status == "Feito":
            continue
        if not record.updated_at:
            rule = "blocked_update_missing" if record.status == "Bloqueada" else "stale"
            message = (
                "Tarefa bloqueada sem atualização do responsável no último dia útil."
                if record.status == "Bloqueada"
                else "Tarefa sem data de atualização do responsável."
            )
            findings.append(Finding(record.source, record.page_id, record.title, rule, message))
            continue
        business_days = _business_days_since(record.updated_at, today)
        if record.status == "Bloqueada":
            if business_days >= 1:
                findings.append(Finding(record.source, record.page_id, record.title, "blocked_update_missing", "Tarefa bloqueada sem atualização do responsável no último dia útil."))
        elif business_days > 2:
            findings.append(Finding(record.source, record.page_id, record.title, "stale", "Tarefa sem atualização do responsável há mais de dois dias úteis."))
    return AuditReport(records=records, findings=findings)
