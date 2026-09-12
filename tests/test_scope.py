import unittest
from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from notion_management.config import Settings
from notion_management.models import AuditReport, Record
from notion_management.scope import in_scope
from notion_management.service import _normalize
from notion_management.snapshot import save_snapshot
from notion_management.gchat import send_webhook


class ScopeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            notion_token="token",
            notion_version="2025-09-03",
            gchat_webhook_url="",
            tasks_id="tasks",
            projects_id="projects",
            coltec_id="coltec",
            requests_id="requests",
            integrations_area_id="area-integracoes",
            manager_id="manager-1",
            team_member_ids=("member-1", "member-2"),
            snapshot_dir="reports/snapshots",
        )

    def test_task_in_area_is_in_scope(self) -> None:
        record = Record(source="tasks", page_id="1", title="Tarefa", area_id="area-integracoes")
        self.assertTrue(in_scope(record, self.settings))

    def test_project_owned_by_team_is_in_scope(self) -> None:
        record = Record(source="projects", page_id="1", title="Projeto", owner_id="member-1")
        self.assertTrue(in_scope(record, self.settings))

    def test_foreign_task_is_excluded(self) -> None:
        record = Record(source="tasks", page_id="1", title="Outra área", area_id="area-financeiro", owner_id="other")
        self.assertFalse(in_scope(record, self.settings))

    def test_coltec_uses_integration_area_or_leandro(self) -> None:
        self.assertTrue(in_scope(Record(source="coltec", page_id="1", title="Ação", area="Integração"), self.settings))
        self.assertTrue(in_scope(Record(source="coltec", page_id="2", title="Ação", owner_id="manager-1"), self.settings))
        self.assertFalse(in_scope(Record(source="coltec", page_id="3", title="Outra área", area="Arquitetura", owner_id="other"), self.settings))

    def test_request_uses_hiveplace_team_or_leandro(self) -> None:
        self.assertTrue(in_scope(Record(source="requests", page_id="1", title="Solicitação", request_team="HIVEPlace"), self.settings))
        self.assertTrue(in_scope(Record(source="requests", page_id="2", title="Solicitação", owner_id="manager-1"), self.settings))
        self.assertFalse(in_scope(Record(source="requests", page_id="3", title="Outra área", request_team="Outra equipe", owner_id="other"), self.settings))

    def test_normalization_preserves_scope_and_system_update_date(self) -> None:
        page = {
            "id": "page-1",
            "properties": {
                "Nome": {"type": "title", "title": [{"plain_text": "Tarefa"}]},
                "Status": {"type": "status", "status": {"name": "Em andamento"}},
                "Responsável": {"type": "people", "people": [{"id": "member-1", "name": "Pessoa"}]},
                "Área": {"type": "relation", "relation": [{"id": "area-integracoes"}]},
                "Última atualização": {"type": "last_edited_time", "last_edited_time": "2026-09-10T12:00:00.000Z"},
            },
        }
        record = _normalize("tasks", page, "Status", "Responsável", "Prazo", "Projeto")
        self.assertEqual(record.area_id, "area-integracoes")
        self.assertEqual(record.owner_id, "member-1")
        self.assertEqual(record.updated_at.isoformat(), "2026-09-10")

    def test_snapshot_uses_iso_date_and_serializes_report(self) -> None:
        with TemporaryDirectory() as directory:
            path = save_snapshot(
                AuditReport(records=[Record(source="tasks", page_id="1", title="Tarefa")]),
                directory,
                today=date(2026, 9, 11),
            )
            self.assertEqual(path, Path(directory) / "2026-09-11.json")
            self.assertIn('"title": "Tarefa"', path.read_text(encoding="utf-8"))

    def test_gchat_thread_key_is_applied_before_send(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        with patch("notion_management.gchat.urlopen", return_value=FakeResponse()) as mocked_urlopen:
            send_webhook("https://chat.example/hook?token=abc", "Alerta", thread_key="gestao-diaria")
        request = mocked_urlopen.call_args.args[0]
        self.assertIn("threadKey=gestao-diaria", request.full_url)


if __name__ == "__main__":
    unittest.main()
