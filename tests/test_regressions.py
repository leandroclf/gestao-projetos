import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from notion_management.alerting import send_pending_alerts
from notion_management.cli import main
from notion_management.management_report import split_management_report
from notion_management.models import AuditReport, Finding, Record, Comment
from notion_management.quality import audit
from notion_management.config import Settings
from notion_management.service import run_audit
from notion_management.snapshot import save_snapshot


class RegressionTest(unittest.TestCase):
    def test_audit_text_path_does_not_access_notify_arguments(self):
        with patch.object(sys, "argv", ["hive-notion", "audit"]), patch("notion_management.cli.run_audit", return_value=AuditReport()):
            self.assertEqual(0, main())

    def test_negative_approval_comment_does_not_satisfy_evidence(self):
        for text in ("teste não realizado", "não aprovado", "sem sucesso"):
            record = Record("tasks", "p", "Aprovação", "Para ser aprovada", "Dono", approver_count=1,
                            approver_names=("Aprovador",), due_date=date.today(),
                            comments=(Comment(date(2026, 1, 1), text),))
            self.assertTrue(any(f.rule == "approval_update_missing" for f in audit([record], today=date(2026, 1, 10)).findings), text)

    def test_reopened_finding_is_sent_again(self):
        finding = Finding("tasks", "p", "Tarefa", "stale", "Atualizar", recipient="Pessoa")
        report = AuditReport([Record("tasks", "p", "Tarefa")], [finding])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            sent = []
            send_pending_alerts(report, path, lambda *args: sent.append(args))
            send_pending_alerts(AuditReport(), path, lambda *args: sent.append(args))
            send_pending_alerts(report, path, lambda *args: sent.append(args))
            self.assertEqual(2, len(sent))

    def test_large_single_block_is_split(self):
        self.assertTrue(all(len(part) <= 100 for part in split_management_report("x" * 250, 100)))

    def test_delivery_failure_is_recorded_as_unknown(self):
        finding = Finding("tasks", "p", "Tarefa", "stale", "Atualizar")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            with self.assertRaises(RuntimeError):
                send_pending_alerts(AuditReport([Record("tasks", "p", "Tarefa")], [finding]), path, lambda *_: (_ for _ in ()).throw(RuntimeError("timeout")))
            state = json.loads(path.read_text())
            self.assertEqual("unknown", next(iter(state["deliveries"].values()))["status"])

    def test_snapshot_with_run_id_is_immutable_per_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = AuditReport(run_id="run-123")
            path = save_snapshot(report, tmp, today=date(2026, 9, 15))
            self.assertEqual("2026-09-15-run-123.json", path.name)

    def test_run_audit_marks_failed_source_without_creating_false_findings(self):
        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.calls = 0

            def query_data_source(self, source_id):
                self.calls += 1
                if self.calls == 2:
                    raise RuntimeError("permission")
                return []

        settings = Settings("token", "2025-09-03", "", "", "tasks", "projects", "coltec", "requests", "area", "manager", (), "reports")
        with patch("notion_management.service.NotionClient", FakeClient):
            report = run_audit(settings, today=date(2026, 9, 15), run_id="run-x")
        self.assertFalse(report.complete)
        self.assertEqual("failed", report.source_results["projects"]["status"])
        self.assertEqual("run-x", report.run_id)


if __name__ == "__main__":
    unittest.main()
