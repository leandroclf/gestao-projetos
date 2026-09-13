import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .models import AuditReport, Finding, Record


ALERT_LABELS = {
    "overdue": "Prazo vencido",
    "stale": "Atualização pendente",
    "due_date_missing": "Tarefa sem prazo",
    "approver_missing": "Aguardando aprovador",
    "owner_missing": "Tarefa sem responsável",
    "urgent_without_project": "Solicitação P0 sem projeto",
}
ALERT_ORDER = tuple(ALERT_LABELS)
MAX_EXAMPLES_PER_OWNER = 8


@dataclass(frozen=True)
class Alert:
    rule: str
    message: str
    fingerprint: str


def _record_by_page(report: AuditReport) -> dict[str, Record]:
    return {record.page_id: record for record in report.records}


def _fingerprint(findings: list[Finding]) -> str:
    value = "\n".join(
        f"{finding.page_id}:{finding.rule}:{finding.title}:{finding.message}"
        for finding in sorted(findings, key=lambda item: (item.rule, item.page_id))
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _format_group(owner: str, findings: list[Finding]) -> str:
    lines = [f"Responsável: {owner} ({len(findings)} pendência(s))"]
    for finding in findings[:MAX_EXAMPLES_PER_OWNER]:
        lines.append(f"- {finding.title}")
    if len(findings) > MAX_EXAMPLES_PER_OWNER:
        lines.append(f"- ... e mais {len(findings) - MAX_EXAMPLES_PER_OWNER} pendência(s) deste responsável")
    return "\n".join(lines)


def build_alerts(report: AuditReport) -> list[Alert]:
    records = _record_by_page(report)
    grouped: dict[str, dict[str, list[Finding]]] = {}
    for finding in report.findings:
        if finding.rule not in ALERT_LABELS:
            continue
        owner = records.get(finding.page_id, Record(source="", page_id="", title="")).owner or "Responsável não identificado"
        grouped.setdefault(finding.rule, {}).setdefault(owner, []).append(finding)

    alerts: list[Alert] = []
    for rule in ALERT_ORDER:
        owners = grouped.get(rule)
        if not owners:
            continue
        findings = [finding for owner_findings in owners.values() for finding in owner_findings]
        sections = [_format_group(owner, owners[owner]) for owner in sorted(owners)]
        message = f"*Alerta de acompanhamento — {ALERT_LABELS[rule]}*\n\n" + "\n\n".join(sections)
        alerts.append(Alert(rule=rule, message=message, fingerprint=_fingerprint(findings)))
    return alerts


def pending_alerts(report: AuditReport) -> list[Alert]:
    return build_alerts(report)


def _read_state(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {"alerts": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"alerts": {}}
    return value if isinstance(value, dict) and isinstance(value.get("alerts"), dict) else {"alerts": {}}


def send_pending_alerts(report: AuditReport, state_path: Path, send: Callable[[str, str], None], force: bool = False) -> list[Alert]:
    state = _read_state(state_path)
    sent: list[Alert] = []
    for alert in pending_alerts(report):
        if not force and state["alerts"].get(alert.rule) == alert.fingerprint:
            continue
        send(alert.message, f"gestao-integracoes-{alert.rule}")
        state["alerts"][alert.rule] = alert.fingerprint
        sent.append(alert)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sent
