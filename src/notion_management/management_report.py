from .models import AuditReport, Comment, Record
from .service import (
    REPORT_COLTEC_COMPLETED_STATUSES,
    REPORT_PROJECT_STATUSES,
    REPORT_REQUEST_STATUSES,
    REPORT_TASK_STATUSES,
)


MANAGEMENT_THREAD_KEY = "gestao-gerencial"
MAX_GCHAT_MESSAGE_CHARS = 20000


def _active(record: Record) -> bool:
    if record.source == "tasks":
        return record.status in REPORT_TASK_STATUSES
    if record.source == "projects":
        return record.status in REPORT_PROJECT_STATUSES
    if record.source == "coltec":
        return record.status not in REPORT_COLTEC_COMPLETED_STATUSES
    return record.source == "requests" and record.status in REPORT_REQUEST_STATUSES


def _date(value) -> str:
    return value.isoformat() if value else "não identificada"


def _comment_text(comment: Comment | None) -> str:
    if not comment or not comment.text:
        return "Nenhum comentário encontrado."
    text = " ".join(comment.text.split())
    return text if len(text) <= 500 else text[:497] + "..."


def _comment_author(comment: Comment | None) -> str:
    return (comment.author_name if comment and comment.author_name else "Autor não identificado")


def _latest(record: Record) -> Comment | None:
    return max(record.comments, key=lambda comment: comment.created_at, default=None)


def _mentions_manager(record: Record, manager_id: str) -> list[Comment]:
    normalized = manager_id.replace("-", "").lower()
    return [
        comment for comment in record.comments
        if any(user_id.replace("-", "").lower() == normalized for user_id in comment.mentioned_user_ids)
    ]


def _record_lines(record: Record, include_due_date: bool = False, prefix: str = "") -> list[str]:
    latest = _latest(record)
    owner = record.owner or "Responsável não identificado"
    lines = [
        f"- {prefix}{record.title} — {record.page_url}",
        f"  Responsável: {owner}",
        f"  Status atual: {record.status}",
    ]
    if include_due_date:
        lines.append(f"  Prazo: {_date(record.due_date)}")
    if record.status == "Para ser aprovada":
        lines.append(f"  Aprovador(es): {', '.join(record.approver_names) or 'Aprovador não identificado'}")
    lines.extend([
        f"  Última atividade/status: {_date(record.updated_at)}",
        f"  Comentário mais recente ({_date(latest.created_at) if latest else 'não identificado'} — Autor: {_comment_author(latest)}): {_comment_text(latest)}",
    ])
    return lines


def render_management_report(report: AuditReport, manager_id: str) -> str:
    records = [record for record in report.records if _active(record) and record.source in {"tasks", "projects", "coltec", "requests"}]
    tasks = [record for record in records if record.source == "tasks"]
    projects = [record for record in records if record.source == "projects"]
    coltec = [record for record in records if record.source == "coltec" and record.owner_id == manager_id]
    requests = [record for record in records if record.source == "requests"]
    mentioned = [(record, _mentions_manager(record, manager_id)) for record in records]
    mentioned = [(record, comments) for record, comments in mentioned if comments]

    lines = ["*Relatório gerencial de acompanhamento — Equipe de Integrações*", ""]
    lines.append(f"Consulta ao Notion: {len(records)} registro(s) — {len(tasks)} tarefa(s), {len(projects)} projeto(s), {len(requests)} demanda(s) de cliente e {len(coltec)} assunto(s)/ação(ões) da COLTEC sob sua responsabilidade.")
    lines.append("Critério: tarefas e projetos ativos; COLTEC sob responsabilidade do gestor e não concluída.")

    lines.extend(["", "*Tarefas ativas*", ""])
    if tasks:
        for record in tasks:
            lines.extend(_record_lines(record, include_due_date=True) + [""])
    else:
        lines.append("Nenhuma tarefa ativa encontrada.\n")

    lines.extend(["*Projetos ativos*", ""])
    if projects:
        for record in projects:
            lines.extend(_record_lines(record) + [""])
    else:
        lines.append("Nenhum projeto ativo encontrado.\n")

    lines.extend(["*Acompanhamento de assuntos e ações da COLTEC sob minha responsabilidade*", ""])
    if coltec:
        for record in coltec:
            lines.extend(_record_lines(record, include_due_date=True) + [""])
    else:
        lines.append("Nenhum assunto ou ação da COLTEC sob minha responsabilidade foi encontrado.\n")

    lines.extend(["*Acompanhamento de demandas de clientes para a área de Integrações*", ""])
    if requests:
        for record in requests:
            lines.extend(_record_lines(record, include_due_date=True) + [""])
    else:
        lines.append("Nenhuma demanda ativa de cliente foi encontrada.\n")

    lines.extend(["*Apoio à pauta e às decisões*", ""])
    lines.append("Os itens abaixo são sugestões para avaliação gerencial; nenhuma demanda é criada ou alterada automaticamente.\n")

    findings_by_page: dict[str, list[str]] = {}
    for finding in report.findings:
        if finding.page_id not in findings_by_page:
            findings_by_page[finding.page_id] = []
        findings_by_page[finding.page_id].append(finding.message)

    pauta_candidates = []
    for record in tasks + projects:
        reasons = findings_by_page.get(record.page_id, [])
        if _mentions_manager(record, manager_id):
            reasons.append("há menção ao gestor nos comentários")
        if reasons:
            pauta_candidates.append((record, list(dict.fromkeys(reasons))))
    lines.append("*Sugestões de assuntos para levar à pauta da COLTEC*\n")
    if pauta_candidates:
        for record, reasons in pauta_candidates:
            lines.extend(_record_lines(record, include_due_date=record.source == "tasks", prefix="Avaliar pauta: ") + [f"  Motivo: {'; '.join(reasons)}", ""])
    else:
        lines.append("Nenhuma sugestão de assunto para a pauta foi identificada.\n")

    lines.append("*Sugestões de demandas para a equipe após decisões da COLTEC*\n")
    if coltec:
        for record in coltec:
            lines.extend(_record_lines(record, include_due_date=True, prefix="Avaliar criação de projeto/tarefa: ") + [
                "  Motivo: assunto ou ação da COLTEC sob responsabilidade do gestor; confirmar a decisão e o desdobramento necessário.",
                "",
            ])
    else:
        lines.append("Nenhum registro da COLTEC sob sua responsabilidade foi encontrado para avaliar desdobramento.\n")

    lines.extend(["*Itens em que Leandro foi mencionado nos comentários*", ""])
    if mentioned:
        for record, comments in mentioned:
            latest_mention = max(comments, key=lambda comment: comment.created_at)
            lines.extend([
                f"- {record.title} — {record.page_url}",
                f"  Responsável: {record.owner or 'Responsável não identificado'}",
                f"  Status atual: {record.status}",
                f"  Menção mais recente ({_date(latest_mention.created_at)} — Autor: {_comment_author(latest_mention)}): {_comment_text(latest_mention)}",
                "",
            ])
    else:
        lines.append("Nenhuma menção estruturada ao usuário gerencial foi encontrada nos comentários.\n")

    return "\n".join(lines).rstrip()


def split_management_report(message: str, max_chars: int = MAX_GCHAT_MESSAGE_CHARS) -> list[str]:
    """Divide o relatório em blocos completos para respeitar o limite do webhook."""
    if len(message) <= max_chars:
        return [message]
    blocks = message.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for block in blocks:
        block_size = len(block) + (2 if current else 0)
        if current and current_size + block_size > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_size = 0
        current.append(block)
        current_size += len(block) + (2 if len(current) > 1 else 0)
    if current:
        chunks.append("\n\n".join(current))
    return chunks
