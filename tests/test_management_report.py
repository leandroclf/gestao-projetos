import unittest
from datetime import date

from notion_management.management_report import render_management_report, render_management_summary, split_management_report
from notion_management.models import AuditReport, Comment, Finding, Record


class ManagementReportTest(unittest.TestCase):
    def test_lists_active_items_latest_comment_and_manager_mentions(self) -> None:
        manager_id = "manager-1"
        task = Record(
            source="tasks",
            page_id="task-1",
            title="Tarefa ativa",
            status="Em Progresso",
            owner="Rafael",
            updated_at=date(2026, 9, 14),
            page_url="https://www.notion.so/task-1",
            comments=(
                Comment(date(2026, 9, 13), "Atualização antiga", author_name="Amanda"),
                Comment(date(2026, 9, 14), "@Leandro, preciso da sua decisão.", (manager_id,), ("Leandro",), author_name="Rafael"),
            ),
        )
        project = Record(
            source="projects",
            page_id="project-1",
            title="Projeto bloqueado",
            status="Blocked",
            owner="Cesar",
            updated_at=date(2026, 9, 12),
            page_url="https://www.notion.so/project-1",
            comments=(Comment(date(2026, 9, 12), "Projeto aguardando retorno."),),
        )
        coltec = Record(
            source="coltec",
            page_id="coltec-1",
            title="Ação COLTEC",
            status="Em andamento",
            owner="Leandro",
            owner_id=manager_id,
            updated_at=date(2026, 9, 13),
            page_url="https://www.notion.so/coltec-1",
            comments=(Comment(date(2026, 9, 13), "Ação em validação."),),
        )
        inactive = Record(source="tasks", page_id="done", title="Concluída", status="Feito")

        message = render_management_report(AuditReport(records=[task, project, coltec, inactive]), manager_id)

        self.assertIn("3 registro(s)", message)
        self.assertIn("Tarefa ativa", message)
        self.assertIn("Responsável: Rafael", message)
        self.assertIn("Comentário mais recente (2026-09-14 — Autor: Rafael): @Leandro, preciso da sua decisão.", message)
        self.assertIn("Autor: Rafael", message)
        self.assertIn("Projeto bloqueado", message)
        self.assertIn("Acompanhamento de assuntos e ações da COLTEC", message)
        self.assertIn("Ação COLTEC", message)
        self.assertIn("Itens em que Leandro foi mencionado", message)
        self.assertIn("Menção mais recente (2026-09-14 — Autor: Rafael)", message)
        self.assertNotIn("Concluída", message)

    def test_splits_large_report_without_losing_blocks(self) -> None:
        message = "cabeçalho\n\n" + "\n\n".join(f"bloco {index}" for index in range(5))
        chunks = split_management_report(message, max_chars=20)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(message, "\n\n".join(chunks))
        self.assertTrue(all(len(chunk) <= 20 for chunk in chunks))

    def test_default_google_chat_limit_is_conservative_for_cards(self) -> None:
        chunks = split_management_report("A" * 4000 + "\n\n" + "B" * 4000 + "\n\nC")

        self.assertGreater(len(chunks), 1)

    def test_derived_sections_do_not_repeat_full_record_details(self) -> None:
        manager_id = "manager-1"
        task = Record(
            source="tasks",
            page_id="task-1",
            title="Tarefa mencionada",
            status="Em Progresso",
            owner="Rafael",
            updated_at=date(2026, 9, 14),
            page_url="https://www.notion.so/task-1",
            comments=(Comment(date(2026, 9, 14), "@Leandro decidir", (manager_id,), author_name="Rafael"),),
        )

        message = render_management_report(AuditReport(records=[task], findings=[]), manager_id)

        self.assertEqual(1, message.count("Comentário mais recente (2026-09-14"))
        self.assertEqual(1, message.count("Responsável: Rafael"))

    def test_incomplete_template_does_not_create_agenda_candidate(self) -> None:
        task = Record(
            source="tasks",
            page_id="task-template",
            title="Tarefa sem template",
            status="Em Progresso",
            owner="Rafael",
            page_url="https://www.notion.so/task-template",
        )
        report = AuditReport(records=[task], findings=[
            Finding("tasks", "task-template", task.title, "template_incomplete", "Documentar template."),
        ])

        message = render_management_report(report, "manager-1")

        self.assertNotIn("Avaliar pauta: Tarefa sem template", message)

    def test_management_summary_contains_indicators_and_only_critical_exceptions(self) -> None:
        critical = Record(
            source="tasks", page_id="blocked", title="Entrega bloqueada", status="Bloqueada",
            owner="Rafael", priority="P0", page_url="https://www.notion.so/blocked",
        )
        attention = Record(
            source="tasks", page_id="missing-date", title="Tarefa sem prazo", status="Em Progresso",
            owner="Cesar", page_url="https://www.notion.so/missing-date",
        )
        report = AuditReport(
            records=[critical, attention],
            findings=[
                Finding("tasks", "blocked", critical.title, "blocked_follow_up", "Solicitar desbloqueio."),
                Finding("tasks", "missing-date", attention.title, "due_date_missing", "Definir prazo."),
            ],
        )

        message = render_management_summary(report, "manager-1", max_exceptions=3)

        self.assertIn("Registros ativos: 2", message)
        self.assertIn("Bloqueios relevantes: 1", message)
        self.assertIn("Itens críticos: 1", message)
        self.assertIn("Entrega bloqueada", message)
        self.assertIn("https://www.notion.so/blocked", message)
        self.assertIn("Tarefa sem prazo", message)
        self.assertIn("*Risco operacional*", message)
        self.assertIn("*Qualidade do fluxo*", message)
        self.assertIn("Itens sem prazo: 1", message)
        self.assertIn("Atualizações pendentes: 0", message)

    def test_management_summary_explains_active_records_and_orphan_tasks(self) -> None:
        project = Record(
            source="projects", page_id="project-1", title="Projeto Atlas", status="Doing",
        )
        linked_task = Record(
            source="tasks", page_id="task-1", title="Tarefa vinculada", status="Em Progresso",
            project_id="project-1",
        )
        orphan_task = Record(
            source="tasks", page_id="task-2", title="Tarefa sem projeto", status="Em Progresso",
        )
        request = Record(source="requests", page_id="request-1", title="Demanda", status="Inbox")
        coltec = Record(source="coltec", page_id="coltec-1", title="Ação", status="Em andamento", owner_id="manager-1")

        message = render_management_summary(
            AuditReport(records=[project, linked_task, orphan_task, request, coltec]),
            "manager-1",
        )

        self.assertIn("Projetos ativos: 1", message)
        self.assertIn("Tarefas vinculadas a projetos: 1", message)
        self.assertIn("Tarefas sem vínculo com projeto: 1", message)
        self.assertIn("Demandas de clientes ativas: 1", message)
        self.assertIn("COLTEC ativo sob responsabilidade: 1", message)
        self.assertIn("Projeto Atlas: 1 tarefa(s)", message)
        self.assertIn("Tarefas sem vínculo", message)
        self.assertIn("Tarefa sem projeto", message)

    def test_summary_excludes_phase_one_disabled_rules_from_critical_and_quality_counts(self) -> None:
        p0_without_project = Record(
            source="requests", page_id="p0", title="Demanda urgente", status="Inbox",
            owner="Rafael", priority="P0", page_url="https://www.notion.so/p0",
        )
        incomplete_template = Record(
            source="tasks", page_id="task-template", title="Tarefa sem template", status="Em Progresso",
            owner="Cesar", page_url="https://www.notion.so/task-template",
        )
        report = AuditReport(
            records=[p0_without_project, incomplete_template],
            findings=[
                Finding("requests", "p0", p0_without_project.title, "urgent_without_project", "Vincular projeto técnico."),
                Finding("tasks", "task-template", incomplete_template.title, "template_incomplete", "Documentar template."),
            ],
        )

        message = render_management_summary(report, "manager-1")

        self.assertIn("Itens críticos: 0", message)
        self.assertIn("Templates incompletos: 0", message)
        self.assertNotIn("Demanda urgente", message)

    def test_empty_management_summary_reports_no_intervention(self) -> None:
        message = render_management_summary(AuditReport(), "manager-1")

        self.assertIn("situação sob controle", message)
        self.assertIn("Itens críticos: 0", message)
        self.assertIn("Nenhuma intervenção gerencial", message)


if __name__ == "__main__":
    unittest.main()
