import unittest
from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from notion_management.config import Settings
from notion_management.models import AuditReport, Record
from notion_management.scope import in_scope
from notion_management.service import _comments, _normalize
from notion_management.snapshot import save_snapshot
from notion_management.gchat import build_visual_payload, send_webhook


class ScopeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            notion_token="token",
            notion_version="2025-09-03",
            gchat_webhook_url="",
            gchat_gerencial_webhook_url="",
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

    def test_task_matches_area_beyond_first_relation_item(self) -> None:
        record = Record(
            source="tasks",
            page_id="1",
            title="Tarefa multi-área",
            area_id="area-financeiro",
            area_ids=("area-financeiro", "area-integracoes"),
            owner_id="other",
        )
        self.assertTrue(in_scope(record, self.settings))

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
                "Área": {"type": "relation", "relation": [{"id": "area-financeiro"}, {"id": "area-integracoes"}]},
                "Última atualização": {"type": "last_edited_time", "last_edited_time": "2026-09-10T12:00:00.000Z"},
            },
        }
        record = _normalize("tasks", page, "Status", "Responsável", "Prazo", "Projeto")
        self.assertEqual(record.area_id, "area-financeiro")
        self.assertEqual(record.area_ids, ("area-financeiro", "area-integracoes"))
        self.assertEqual(record.owner_id, "member-1")
        self.assertEqual(record.updated_at.isoformat(), "2026-09-10")

    def test_comments_preserve_author(self) -> None:
        comments = _comments([{
            "created_time": "2026-09-14T10:00:00.000Z",
            "created_by": {"id": "author-1", "name": "Amanda"},
            "rich_text": [{"plain_text": "Atualização registrada."}],
        }])

        self.assertEqual("author-1", comments[0].author_id)
        self.assertEqual("Amanda", comments[0].author_name)

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

    def test_visual_payload_contains_branding_and_notion_button(self) -> None:
        payload = build_visual_payload("*Prazo vencido*\n\n- Tarefa — https://www.notion.so/page-1", "https://example.com/logo.png", category="overdue")

        card = payload["cardsV2"][0]["card"]
        self.assertEqual("Gestão de Projetos", card["header"]["title"])
        self.assertEqual("https://example.com/logo.png", card["header"]["imageUrl"])
        self.assertIn("Abrir no Notion", str(payload))
        self.assertIn('#B3261E', str(payload))
        self.assertNotIn("text", payload)
        self.assertIn('#1A1A1C', str(payload))

    def test_visual_payload_uses_explicit_semantic_category(self) -> None:
        payload = build_visual_payload("*Aguardando aprovação*", category="approval")

        self.assertIn('#7A4B00', str(payload))

    def test_visual_payload_unknown_category_is_neutral(self) -> None:
        payload = build_visual_payload("Informação", category="unknown")

        self.assertIn('#1A1A1C', str(payload))


if __name__ == "__main__":
    unittest.main()
