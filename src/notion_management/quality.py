from datetime import date, timedelta

from .models import AuditReport, Comment, Finding, Record


TASK_REVIEW_STATUSES = {"Em Progresso", "Bloqueada", "Para ser aprovada"}
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


def _latest_comment(record: Record) -> Comment | None:
    return max(enumerate(record.comments), key=lambda item: (item[1].created_at_time.timestamp() if item[1].created_at_time else 0, item[1].created_at.toordinal(), item[0]), default=(0, None))[1]


def _latest_comment_date(record: Record) -> date | None:
    latest = _latest_comment(record)
    return latest.created_at if latest else None


def _has_comment_on(record: Record, day: date) -> bool:
    return any(comment.created_at == day for comment in record.comments)


def _has_approval_evidence(latest_comment: Comment | None) -> bool:
    """A evidência só vale enquanto for o comentário mais recente da aprovação."""
    if not latest_comment:
        return False
    positive = ("aprovado", "aprovada", "validado", "validada", "sucesso", "passou", "evidência positiva")
    negative = ("não realizado", "nao realizado", "não aprovado", "nao aprovado", "pendente", "reprovado", "reprovada", "falhou", "sem sucesso", "sem evidência", "sem evidencia")
    text = latest_comment.text.casefold()
    if any(term in text for term in negative):
        return False
    return any(term in text for term in positive)


def audit(records: list[Record], today: date | None = None) -> AuditReport:
    today = today or date.today()
    findings: list[Finding] = []
    for record in records:
        if record.source == "tasks" and record.status == "Em Progresso" and not _has_comment_on(record, today):
            findings.append(Finding(
                record.source,
                record.page_id,
                record.title,
                "progress_update_missing",
                "Tarefa em progresso sem comentário de andamento no dia atual.",
                recipient=record.owner,
                url=record.page_url,
            ))
        if record.source == "requests" and record.status in ACTIVE_REQUEST_STATUSES and record.priority == "P0" and not record.project_id:
            findings.append(Finding(record.source, record.page_id, record.title, "urgent_without_project", "Solicitação P0 sem projeto técnico relacionado."))
        if record.source != "tasks" or record.status not in TASK_REVIEW_STATUSES:
            if record.source == "projects" and record.status in ACTIVE_PROJECT_STATUSES and record.template_missing:
                findings.append(Finding(record.source, record.page_id, record.title, "template_incomplete", f"Projeto sem documentação do template: {', '.join(record.template_missing)}.", recipient=record.owner, url=record.page_url))
            continue
        if record.template_missing:
            findings.append(Finding(record.source, record.page_id, record.title, "template_incomplete", f"Tarefa sem documentação do template: {', '.join(record.template_missing)}.", recipient=record.owner, url=record.page_url))
        if not record.owner:
            findings.append(Finding(record.source, record.page_id, record.title, "owner_missing", "Tarefa em status controlado sem responsável."))
        if not record.due_date:
            findings.append(Finding(record.source, record.page_id, record.title, "due_date_missing", "Tarefa em status controlado sem prazo."))
        if record.status == "Para ser aprovada" and record.approver_count < 1:
            findings.append(Finding(record.source, record.page_id, record.title, "approver_missing", "Tarefa aguardando aprovação sem pelo menos um aprovador."))
        if record.due_date and record.due_date < today and record.status not in {"Feito", "Bloqueada"}:
            findings.append(Finding(record.source, record.page_id, record.title, "overdue", "Prazo vencido para tarefa ainda não concluída."))
        recipient = record.owner
        rule = "stale"
        message = "Tarefa sem data de atualização nos comentários."
        update_date = max(filter(None, (record.updated_at, _latest_comment_date(record))), default=None)
        if record.status == "Para ser aprovada":
            recipient = ", ".join(record.approver_names) or "Aprovador não identificado"
            rule = "approval_update_missing"
            message = "Aprovador deverá incluir evidências dos testes nos comentários e registrar como feito caso sucesso nos testes."
            latest_comment = _latest_comment(record)
            update_date = latest_comment.created_at if latest_comment else None
            if _has_approval_evidence(latest_comment):
                continue
        elif record.status == "Bloqueada":
            recipient = record.comment_recipient or record.owner
            rule = "blocked_follow_up"
            message = "Ação necessária: revisar o comentário mais recente do bloqueio, registrar o avanço ou desbloqueio e conduzir a tarefa até Feito."
            update_date = _latest_comment_date(record)
        if not update_date:
            findings.append(Finding(record.source, record.page_id, record.title, rule, message, recipient=recipient, url=record.page_url))
            continue
        business_days = _business_days_since(update_date, today)
        if business_days > 2:
            findings.append(Finding(record.source, record.page_id, record.title, rule, message if rule != "stale" else "Tarefa sem atualização do responsável há mais de dois dias úteis.", recipient=recipient, url=record.page_url))
    return AuditReport(records=records, findings=findings)
