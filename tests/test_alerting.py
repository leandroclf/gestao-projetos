import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from notion_management.alerting import build_alerts, build_operational_digest, pending_alerts, progress_update_rules, scheduled_rules, send_pending_alerts, update_alert_lifecycle, validation_message
from notion_management.models import AuditReport, Comment, Finding, Record


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

    def test_includes_responsible_next_to_each_task(self) -> None:
        message = next(alert.message for alert in build_alerts(self._report()) if alert.rule == "overdue")
        self.assertIn("- Tarefa vencida — https://www.notion.so/1\n  Responsável: Rafael", message)

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
            self.assertEqual(2, len(json.loads(state_path.read_text())["alerts"]))

    def test_alert_exposes_visual_category_from_quality_rule(self) -> None:
        alert = next(alert for alert in pending_alerts(self._report()) if alert.rule == "overdue")

        self.assertEqual("overdue", alert.category)
    def test_empty_or_non_actionable_report_produces_no_alert(self) -> None:
        self.assertEqual([], pending_alerts(AuditReport()))

    def test_template_incomplete_alert_is_disabled_for_phase_two(self) -> None:
        report = AuditReport(
            records=[Record(source="tasks", page_id="1", title="Template", owner="Rafael")],
            findings=[Finding("tasks", "1", "Template", "template_incomplete", "Documentar template.")],
        )
        self.assertEqual([], pending_alerts(report))

    def test_p0_alert_is_disabled_and_rule_filter_selects_categories(self) -> None:
        report = AuditReport(findings=[Finding("requests", "1", "P0", "urgent_without_project", "Criar projeto.")])
        self.assertEqual([], pending_alerts(report))
        report = self._report()
        self.assertEqual(["overdue"], [alert.rule for alert in pending_alerts(report, rules={"overdue"})])

    def test_schedule_adds_missing_due_date_only_on_tuesday_and_thursday(self) -> None:
        self.assertNotIn("due_date_missing", scheduled_rules(0))
        self.assertIn("due_date_missing", scheduled_rules(1))
        self.assertIn("due_date_missing", scheduled_rules(3))

    def test_progress_update_schedule_runs_only_on_business_days(self) -> None:
        self.assertEqual({"progress_update_missing"}, progress_update_rules(0))
        self.assertEqual({"progress_update_missing"}, progress_update_rules(4))
        self.assertEqual(set(), progress_update_rules(5))

    def test_progress_update_alert_has_specific_label_and_category(self) -> None:
        report = AuditReport(
            records=[Record(source="tasks", page_id="1", title="Sem andamento", status="Em Progresso", owner="Rafael", page_url="https://www.notion.so/1")],
            findings=[Finding("tasks", "1", "Sem andamento", "progress_update_missing", "Tarefa em progresso sem comentário de andamento no dia atual.")],
        )
        alert = build_alerts(report)[0]
        self.assertIn("Acompanhamento em progresso sem comentário do dia", alert.message)
        self.assertEqual("progress", alert.category)

    def test_morning_escalation_is_sent_only_after_previous_afternoon_alert(self) -> None:
        report = AuditReport(
            records=[Record(source="tasks", page_id="1", title="Sem andamento", status="Em Progresso", owner="Rafael", page_url="https://www.notion.so/1")],
            findings=[Finding("tasks", "1", "Sem andamento", "progress_update_missing", "Tarefa em progresso sem comentário de andamento no dia atual.")],
        )
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "alerts.json"
            sent: list[str] = []
            publish = lambda message, thread: sent.append(message)
            send_pending_alerts(report, state_path, publish, thread_key="andamento", rules={"progress_update_missing"}, today=date(2026, 9, 15))

            report.findings = []
            report.records[0] = Record(source="tasks", page_id="1", title="Sem andamento", status="Em Progresso", owner="Rafael", page_url="https://www.notion.so/1")
            send_pending_alerts(report, state_path, publish, thread_key="geral", rules=scheduled_rules(1), digest=True, today=date(2026, 9, 16))

            self.assertEqual(2, len(sent))
            self.assertIn("Pendência crítica de andamento", sent[-1])

    def test_current_day_comment_prevents_afternoon_and_morning_escalation(self) -> None:
        report = AuditReport(
            records=[Record(source="tasks", page_id="1", title="Atualizada", status="Em Progresso", owner="Rafael", comments=(Comment(date(2026, 9, 16)),), page_url="https://www.notion.so/1")],
            findings=[],
        )
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "alerts.json"
            sent: list[str] = []
            previous = AuditReport(
                records=[Record(source="tasks", page_id="1", title="Atualizada", status="Em Progresso", owner="Rafael", page_url="https://www.notion.so/1")],
                findings=[Finding("tasks", "1", "Atualizada", "progress_update_missing", "Sem comentário.")],
            )
            send_pending_alerts(previous, state_path, lambda message, thread: sent.append(message), thread_key="andamento", rules={"progress_update_missing"}, today=date(2026, 9, 15))
            send_pending_alerts(report, state_path, lambda message, thread: sent.append(message), thread_key="geral", rules=scheduled_rules(2), digest=True, today=date(2026, 9, 16))
            send_pending_alerts(report, state_path, lambda message, thread: sent.append(message), thread_key="andamento", rules={"progress_update_missing"}, today=date(2026, 9, 16))
            self.assertEqual(1, len(sent))
            self.assertNotIn("Pendência crítica de andamento", sent[0])

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
        report = AuditReport(records=[Record(source="tasks", page_id="1", title="Aprovação", status="Para ser aprovada", owner="Leandro", approver_names=("Camila",), page_url="https://www.notion.so/1")], findings=[Finding("tasks", "1", "Aprovação", "approval_update_missing", "Aprovador deverá incluir evidências dos testes nos comentários e registrar como feito caso sucesso nos testes.")])
        alert = build_alerts(report)[0]
        self.assertIn("Aguardando aprovação", alert.message)
        self.assertIn("evidências dos testes", alert.message)
        self.assertIn("Aprovador(es): Camila", alert.message)

    def test_alert_lifecycle_marks_new_maintained_and_resolved_findings(self) -> None:
        initial = AuditReport(findings=[Finding("tasks", "1", "Tarefa", "overdue", "Vencida")])
        state = {"lifecycle": {}}

        update_alert_lifecycle(state, initial)
        self.assertEqual("aberto", state["lifecycle"]["tasks:1:overdue"]["status"])

        update_alert_lifecycle(state, initial)
        self.assertEqual("mantido", state["lifecycle"]["tasks:1:overdue"]["status"])

        update_alert_lifecycle(state, AuditReport())
        self.assertEqual("resolvido", state["lifecycle"]["tasks:1:overdue"]["status"])

    def test_alert_lifecycle_marks_reopened_finding(self) -> None:
        state = {"lifecycle": {}}
        report = AuditReport(findings=[Finding("tasks", "1", "Tarefa", "overdue", "Vencida")])

        update_alert_lifecycle(state, report)
        update_alert_lifecycle(state, AuditReport())
        update_alert_lifecycle(state, report)

        self.assertEqual("reaberto", state["lifecycle"]["tasks:1:overdue"]["status"])

    def test_operational_digest_shows_one_entry_when_item_has_multiple_findings(self) -> None:
        record = Record("tasks", "1", "Entrega", "Em Progresso", "Rafael", page_url="https://www.notion.so/1")
        report = AuditReport(records=[record], findings=[
            Finding("tasks", "1", "Entrega", "stale", "Registrar atualização."),
            Finding("tasks", "1", "Entrega", "overdue", "Atualizar prazo."),
        ])

        digest = build_operational_digest(report, rules={"stale", "overdue"})

        self.assertIsNotNone(digest)
        self.assertEqual("operational_digest", digest.rule)
        self.assertEqual(1, digest.message.count("- Entrega"))
        self.assertIn("Prazo vencido", digest.message)
        self.assertNotIn("Registrar atualização", digest.message)
