import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from notion_management.alerting import build_alerts, pending_alerts, send_pending_alerts, validation_message
from notion_management.models import AuditReport, Finding, Record


class AlertingTest(unittest.TestCase):
    def _report(self) -> AuditReport:
        records = [
            Record(source="tasks", page_id="1", title="Tarefa vencida", status="Em Progresso", owner="Rafael", due_date=date.today() - timedelta(days=1), page_url="https://www.notion.so/1"),
            Record(source="tasks", page_id="2", title="Tarefa sem atualização", status="Bloqueada", owner="Cesar", due_date=date.today()),
        ]
        findings = [
            Finding("tasks", "1", "Tarefa vencida", "overdue", "Prazo vencido para tarefa ainda não concluída."),
            Finding("tasks", "2", "Tarefa sem atualização", "stale", "Tarefa sem atualização do responsável há mais de dois dias úteis."),
        ]
        return AuditReport(records=records, findings=findings)

    def test_builds_one_message_per_alert_type_with_responsible(self) -> None:
        alerts = build_alerts(self._report())
        self.assertEqual({"overdue", "stale"}, {alert.rule for alert in alerts})
        self.assertIn("Rafael", next(alert.message for alert in alerts if alert.rule == "overdue"))
        self.assertIn("Tarefa vencida", next(alert.message for alert in alerts if alert.rule == "overdue"))
        self.assertIn("https://www.notion.so/1", next(alert.message for alert in alerts if alert.rule == "overdue"))

    def test_only_changed_alerts_are_sent_and_force_resends(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "alerts.json"
            sent: list[str] = []
            publish = lambda message, thread: sent.append(f"{thread}: {message}")
            send_pending_alerts(self._report(), state_path, publish)
            self.assertEqual(2, len(sent))
            send_pending_alerts(self._report(), state_path, publish)
            self.assertEqual(2, len(sent))
            send_pending_alerts(self._report(), state_path, publish, force=True)
            self.assertEqual(4, len(sent))
            self.assertEqual(2, len(json.loads(state_path.read_text()) ["alerts"]))

    def test_empty_or_non_actionable_report_produces_no_alert(self) -> None:
        self.assertEqual([], pending_alerts(AuditReport()))

    def test_limits_each_responsible_group_to_three_examples(self) -> None:
        report = self._report()
        report.findings.extend(
            Finding("tasks", str(index), f"Pendência {index}", "overdue", "Prazo vencido.")
            for index in range(3, 7)
        )
        report.records.extend(
            Record(source="tasks", page_id=str(index), title=f"Pendência {index}", status="Em Progresso", owner="Rafael")
            for index in range(3, 7)
        )
        message = next(alert.message for alert in build_alerts(report) if alert.rule == "overdue")
        self.assertIn("e mais 2 pendência(s) deste responsável", message)

    def test_validation_message_contains_only_current_alerts(self) -> None:
        message = validation_message(self._report())
        self.assertIn("Pendências atuais", message)
        self.assertIn("Tarefa vencida", message)
        self.assertIn("Rafael", message)

    def test_approval_alert_uses_new_label_and_action(self) -> None:
        report = AuditReport(records=[Record(source="tasks", page_id="1", title="Aprovação", owner="Leandro", page_url="https://www.notion.so/1")], findings=[Finding("tasks", "1", "Aprovação", "approval_update_missing", "Aprovador deverá incluir evidências dos testes nos comentários e registrar como feito caso sucesso nos testes.")])
        alert = build_alerts(report)[0]
        self.assertIn("Aguardando aprovação", alert.message)
        self.assertIn("evidências dos testes", alert.message)
