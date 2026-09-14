import unittest

from notion_management.template import missing_sections


def heading(text: str) -> dict:
    return {"type": "heading_3", "heading_3": {"rich_text": [{"plain_text": text}]}}


class TemplateTest(unittest.TestCase):
    def test_task_reports_missing_template_sections(self) -> None:
        missing = missing_sections("tasks", {}, [heading("Motivação e Contexto")])
        self.assertEqual(("Critério De Pronto", "Anotações"), missing)

    def test_project_requires_description_and_all_sections(self) -> None:
        missing = missing_sections("projects", {"Descrição": {"rich_text": []}}, [])
        self.assertEqual(("Descrição", "Motivação E Contexto", "Definição De Pronto E De Sucesso", "Aspectos Críticos E Condições De Contorno", "Outros Pontos Relevantes", "Tarefas E Desenvolvimento"), missing)
