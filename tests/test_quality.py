import unittest
from datetime import date, timedelta

from notion_management.models import Comment, Record
from notion_management.quality import audit


class QualityTest(unittest.TestCase):
    def test_flags_blocked_task_with_stale_update_but_not_overdue_alert(self) -> None:
        report = audit(
            [Record(source="tasks", page_id="1", title="Integração", status="Bloqueada", due_date=date.today() - timedelta(days=1), updated_at=date.today() - timedelta(days=6))]
        )
        rules = {finding.rule for finding in report.findings}
        self.assertTrue({"owner_missing", "stale"} <= rules)
        self.assertNotIn("overdue", rules)


    def test_task_without_project_is_allowed(self) -> None:
        report = audit([Record(source="tasks", page_id="1", title="Independente", status="Em Progresso", owner="Pessoa", due_date=date.today(), updated_at=date.today())])
        self.assertNotIn("project_missing", {finding.rule for finding in report.findings})


    def test_owner_and_due_date_apply_only_to_active_controlled_statuses(self) -> None:
        backlog = audit([Record(source="tasks", page_id="1", title="Backlog", status="Backlog")])
        feito = audit([Record(source="tasks", page_id="2", title="Feito", status="Feito")])
        self.assertNotIn("owner_missing", {finding.rule for finding in backlog.findings})
        self.assertNotIn("due_date_missing", {finding.rule for finding in backlog.findings})
        self.assertEqual([], feito.findings)


    def test_controlled_task_requires_approver_only_when_waiting_approval(self) -> None:
        report = audit([
            Record(source="tasks", page_id="1", title="Aguardando", status="Para ser aprovada", owner="Pessoa", due_date=date.today(), approver_count=0, updated_at=date.today()),
            Record(source="tasks", page_id="2", title="Em andamento", status="Em Progresso", owner="Pessoa", due_date=date.today(), approver_count=0, updated_at=date.today()),
        ])
        findings = {(finding.page_id, finding.rule) for finding in report.findings}
        self.assertIn(("1", "approver_missing"), findings)
        self.assertNotIn(("2", "approver_missing"), findings)


    def test_business_day_cadence_ignores_weekend(self) -> None:
        report = audit([
            Record(source="tasks", page_id="1", title="Atualizada na sexta", status="Em Progresso", owner="Pessoa", due_date=date(2026, 9, 14), updated_at=date(2026, 9, 11)),
        ], today=date(2026, 9, 13))
        self.assertNotIn("stale", {finding.rule for finding in report.findings})

    def test_approval_update_is_directed_to_approver_and_requires_evidence(self) -> None:
        report = audit([Record(source="tasks", page_id="1", title="Aprovação", status="Para ser aprovada", owner="Rafael", approver_names=("Leandro",), due_date=date.today())], today=date(2026, 9, 13))
        finding = next(finding for finding in report.findings if finding.rule == "approval_update_missing")
        self.assertEqual("Leandro", finding.recipient)

    def test_blocked_update_is_directed_to_last_team_member_mentioned(self) -> None:
        report = audit([Record(
            source="tasks", page_id="1", title="Bloqueada", status="Bloqueada", owner="Rafael", due_date=date.today(),
            updated_at=date(2026, 9, 12),
            comments=(Comment(date(2026, 9, 7), "Cesar, consegue verificar?", ("cesar-id",), ("Cesar",)),),
            comment_recipient="Cesar",
        )], today=date(2026, 9, 13))
        finding = next(finding for finding in report.findings if finding.rule == "blocked_follow_up")
        self.assertEqual("Cesar", finding.recipient)


    def test_ignores_completed_records(self) -> None:
        report = audit([Record(source="tasks", page_id="1", title="Concluída", status="Feito", owner="Pessoa", due_date=date.today())])
        self.assertEqual(report.findings, [])


    def test_flags_p0_request_without_project(self) -> None:
        report = audit([Record(source="requests", page_id="1", title="P0", status="Inbox", owner="Rafael", priority="P0")])
        self.assertTrue(any(f.rule == "urgent_without_project" for f in report.findings))
