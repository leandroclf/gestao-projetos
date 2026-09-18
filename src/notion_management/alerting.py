import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Callable

import fcntl

from .models import AuditReport, Finding, Record, has_comment_on


ALERT_LABELS = {
    "overdue": "Prazo vencido",
    "stale": "Atualização pendente",
    "progress_update_missing": "Acompanhamento em progresso sem comentário do dia",
    "approval_update_missing": "Aguardando aprovação",
    "blocked_follow_up": "Ação para desbloqueio",
    "template_incomplete": "Template incompleto",
    "due_date_missing": "Tarefa sem prazo",
    "approver_missing": "Aguardando aprovador",
    "owner_missing": "Tarefa sem responsável",
    "urgent_without_project": "Solicitação P0 sem projeto",
}
ALERT_ORDER = tuple(ALERT_LABELS)
MAX_EXAMPLES_PER_OWNER = 3
DEFAULT_THREAD_KEY = "gestao-integracoes"
DISABLED_ALERT_RULES = {"template_incomplete", "urgent_without_project"}
DAILY_ALERT_RULES = {"overdue", "stale", "approval_update_missing", "blocked_follow_up"}
RULE_PRIORITY = {
    "blocked_follow_up": 0,
    "overdue": 1,
    # Falta de aprovador é a causa raiz; cobrar um "aprovador não identificado"
    # antes de resolver isso apenas confundiria o dono da tarefa.
    "approver_missing": 2,
    "approval_update_missing": 3,
    "stale": 4,
    "progress_update_missing": 5,
    "due_date_missing": 6,
    "owner_missing": 7,
}

INTRO_MESSAGE = """*Evolução do acompanhamento — Equipe de Integrações*

Estamos iniciando uma evolução no acompanhamento de projetos e tarefas para facilitar a gestão, dar mais visibilidade às pendências e melhorar a qualidade das entregas.

Os alertas serão objetivos e enviados somente quando houver necessidade de atuação. O Notion continua sendo a fonte oficial, e toda atualização deve ser registrada nos comentários da tarefa com a evolução, impedimento, evidência ou próximo passo.

A proposta é reduzir cobranças manuais, antecipar riscos e apoiar a equipe e a liderança no acompanhamento dos compromissos."""


@dataclass(frozen=True)
class Alert:
    rule: str
    message: str
    fingerprint: str
    category: str = "general"


def alert_category(rule: str) -> str:
    """Mapeia uma regra de qualidade para a categoria visual do card."""
    return {
        "overdue": "overdue",
        "blocked_follow_up": "blocked",
        "approval_update_missing": "approval",
        "approver_missing": "approval",
        "stale": "stale",
        "due_date_missing": "stale",
        "progress_update_missing": "progress",
    }.get(rule, "general")


def _record_by_page(report: AuditReport) -> dict[str, Record]:
    return {record.page_id: record for record in report.records}


def _fingerprint(findings: list[Finding]) -> str:
    value = "\n".join(
        f"{finding.page_id}:{finding.rule}:{finding.title}:{finding.message}:{finding.recipient}:{finding.url}"
        for finding in sorted(findings, key=lambda item: (item.rule, item.page_id, item.recipient))
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _format_group(owner: str, findings: list[Finding], records: dict[str, Record]) -> str:
    lines = [f"Responsável: {owner} ({len(findings)} pendência(s))"]
    for finding in findings[:MAX_EXAMPLES_PER_OWNER]:
        link = f" — {finding.url}" if finding.url else ""
        lines.append(f"- {finding.title}{link}")
        lines.append(f"  Responsável: {owner}")
        record = records.get(finding.page_id)
        if record and record.status == "Para ser aprovada":
            approvers = ", ".join(record.approver_names) or "Aprovador não identificado"
            lines.append(f"  Aprovador(es): {approvers}")
        lines.append(f"  Ação: {finding.message}")
    if len(findings) > MAX_EXAMPLES_PER_OWNER:
        lines.append(f"- ... e mais {len(findings) - MAX_EXAMPLES_PER_OWNER} pendência(s) deste responsável")
    return "\n".join(lines)


def build_alerts(report: AuditReport, rules: set[str] | None = None) -> list[Alert]:
    records = _record_by_page(report)
    grouped: dict[str, dict[str, list[Finding]]] = {}
    for finding in report.findings:
        if finding.rule not in ALERT_LABELS or finding.rule in DISABLED_ALERT_RULES or (rules is not None and finding.rule not in rules):
            continue
        record = records.get(finding.page_id, Record(source="", page_id="", title=""))
        recipient = finding.recipient or record.owner or "Responsável não identificado"
        enriched = replace(finding, recipient=recipient, url=finding.url or record.page_url)
        grouped.setdefault(finding.rule, {}).setdefault(recipient, []).append(enriched)

    alerts: list[Alert] = []
    for rule in ALERT_ORDER:
        owners = grouped.get(rule)
        if not owners:
            continue
        findings = [finding for owner_findings in owners.values() for finding in owner_findings]
        sections = [_format_group(owner, owners[owner], records) for owner in sorted(owners)]
        message = f"*Alerta de acompanhamento — {ALERT_LABELS[rule]}*\n\n" + "\n\n".join(sections)
        alerts.append(Alert(rule=rule, message=message, fingerprint=_fingerprint(findings), category=alert_category(rule)))
    return alerts


def build_operational_digest(report: AuditReport, rules: set[str] | None = None) -> Alert | None:
    """Consolida regras do mesmo item em uma mensagem operacional única."""
    records = _record_by_page(report)
    selected: dict[str, Finding] = {}
    for finding in report.findings:
        if finding.rule not in ALERT_LABELS or finding.rule in DISABLED_ALERT_RULES or (rules is not None and finding.rule not in rules):
            continue
        record = records.get(finding.page_id, Record(source="", page_id="", title=""))
        enriched = replace(finding, recipient=finding.recipient or record.owner or "Responsável não identificado", url=finding.url or record.page_url)
        current = selected.get(finding.page_id)
        if current is None or (RULE_PRIORITY.get(finding.rule, 99), ALERT_ORDER.index(finding.rule)) < (RULE_PRIORITY.get(current.rule, 99), ALERT_ORDER.index(current.rule)):
            selected[finding.page_id] = enriched
    if not selected:
        return None

    by_owner: dict[str, list[Finding]] = {}
    for finding in selected.values():
        by_owner.setdefault(finding.recipient, []).append(finding)
    lines = ["*Digest operacional — Equipe de Integrações*", "", f"{len(selected)} item(ns) exigem acompanhamento."]
    for owner in sorted(by_owner):
        findings = sorted(by_owner[owner], key=lambda item: (RULE_PRIORITY.get(item.rule, 99), item.title))
        lines.extend(["", f"Responsável: {owner} ({len(findings)} item(ns))"])
        for finding in findings[:MAX_EXAMPLES_PER_OWNER]:
            label = ALERT_LABELS[finding.rule]
            link = f" — {finding.url}" if finding.url else ""
            lines.append(f"- {finding.title}{link}")
            lines.append(f"  Situação: {label}; ação: {finding.message}")
        if len(findings) > MAX_EXAMPLES_PER_OWNER:
            lines.append(f"- ... e mais {len(findings) - MAX_EXAMPLES_PER_OWNER} item(ns) no relatório do Notion")
    return Alert(rule="operational_digest", message="\n".join(lines), fingerprint=_fingerprint(list(selected.values())), category="general")


def pending_alerts(report: AuditReport, rules: set[str] | None = None, digest: bool = False) -> list[Alert]:
    alert = build_operational_digest(report, rules=rules) if digest else None
    return [alert] if alert else [] if digest else build_alerts(report, rules=rules)


def scheduled_rules(weekday: int) -> set[str]:
    rules = set(DAILY_ALERT_RULES) | {"progress_update_missing"}
    if weekday in {1, 3}:
        rules.add("due_date_missing")
    return rules


def progress_update_rules(weekday: int) -> set[str]:
    """Seleciona o alerta de andamento para o ciclo do fim do expediente."""
    return {"progress_update_missing"} if weekday < 5 else set()


def validation_message(report: AuditReport) -> str:
    alerts = pending_alerts(report)
    if not alerts:
        return "*Validação inicial — Equipe de Integrações*\n\nNenhuma pendência acionável foi encontrada no escopo atual."
    return "*Validação inicial — Pendências atuais da Equipe de Integrações*\n\n" + "\n\n".join(alert.message for alert in alerts)


def update_alert_lifecycle(state: dict, report: AuditReport) -> None:
    """Atualiza o ciclo de vida por achado sem remover o histórico resolvido."""
    lifecycle = state.setdefault("lifecycle", {})
    current: dict[str, Finding] = {
        f"{finding.source}:{finding.page_id}:{finding.rule}": finding
        for finding in report.findings
        if finding.rule in ALERT_LABELS and finding.rule not in DISABLED_ALERT_RULES
    }
    for key, finding in current.items():
        previous = lifecycle.get(key, {})
        previous_status = previous.get("status")
        status = "reaberto" if previous_status == "resolvido" else "mantido" if previous_status else "aberto"
        lifecycle[key] = {"status": status, "title": finding.title, "rule": finding.rule}
    for key, value in lifecycle.items():
        if key not in current and value.get("status") not in {None, "resolvido"}:
            value["status"] = "resolvido"


def _read_state(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {"alerts": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"alerts": {}}
    return value if isinstance(value, dict) and isinstance(value.get("alerts"), dict) else {"alerts": {}}


def _write_state(path: Path, state: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(state, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = temporary.name
    os.replace(temporary_path, path)


@contextmanager
def _state_lock(path: Path):
    """Serializa execuções concorrentes para não publicar o mesmo alerta duas vezes."""
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def send_pending_alerts(report: AuditReport, state_path: Path, send: Callable[[str, str], None], force: bool = False, thread_key: str = DEFAULT_THREAD_KEY, rules: set[str] | None = None, send_with_category: Callable[[str, str, str], None] | None = None, digest: bool = False, today: date | None = None) -> list[Alert]:
    with _state_lock(state_path):
        state = _read_state(state_path)
        today = today or date.today()
        update_alert_lifecycle(state, report)
        sent: list[Alert] = []
        all_current = {alert.rule: alert.fingerprint for alert in pending_alerts(report, digest=digest)}
        # O filtro diário seleciona entregas; ele nunca deve marcar o achado como resolvido.
        state["alerts"] = {rule: fp for rule, fp in state["alerts"].items() if rule in all_current}
        selected = pending_alerts(report, rules=rules, digest=digest)
        deliveries = state.setdefault("deliveries", {})
        for alert in selected:
            if not force and state["alerts"].get(alert.rule) == alert.fingerprint:
                continue
            delivery_key = f"{alert.rule}:{alert.fingerprint}:{thread_key}"
            deliveries[delivery_key] = {"status": "pending"}
            _write_state(state_path, state)
            try:
                if send_with_category:
                    send_with_category(alert.message, thread_key, alert.category)
                else:
                    send(alert.message, thread_key)
            except Exception:
                # Um timeout pode ocorrer depois de o serviço remoto aceitar a mensagem.
                # Mantemos estado desconhecido e permitimos nova tentativa consciente.
                deliveries[delivery_key] = {"status": "unknown"}
                state["alerts"].pop(alert.rule, None)
                _write_state(state_path, state)
                raise
            deliveries[delivery_key] = {"status": "sent"}
            state["alerts"][alert.rule] = alert.fingerprint
            _write_state(state_path, state)
            sent.append(alert)
        _write_state(state_path, state)
        return sent
