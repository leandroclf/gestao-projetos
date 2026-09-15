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


class RegressionTest(unittest.TestCase):
    def test_audit_text_path_does_not_access_notify_arguments(self):
        with patch.object(sys, "argv", ["hive-notion", "audit"]), patch("notion_management.cli.run_audit", return_value=AuditReport()):
            self.assertEqual(0, main())

    def test_negative_approval_comment_does_not_satisfy_evidence(self):
        record = Record("tasks", "p", "Aprovação", "Para ser aprovada", "Dono", approver_count=1,
                        approver_names=("Aprovador",), due_date=date.today(),
                        comments=(Comment(date(2026, 1, 1), "teste não realizado"),))
        self.assertTrue(any(f.rule == "approval_update_missing" for f in audit([record], today=date(2026, 1, 10)).findings))

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


if __name__ == "__main__":
    unittest.main()
