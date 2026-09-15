import argparse
import json
from datetime import datetime
from dataclasses import asdict
from pathlib import Path

from .alerting import DEFAULT_THREAD_KEY, INTRO_MESSAGE, pending_alerts, scheduled_rules, send_pending_alerts, validation_message
from .config import Settings
from .gchat import build_visual_payload, send_webhook
from .management_report import MANAGEMENT_THREAD_KEY, render_management_report, split_management_report
from .snapshot import save_snapshot
from .service import render_markdown, run_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria gerencial das fontes de Integrações no Notion.")
    sub = parser.add_subparsers(dest="command", required=True)
    audit_parser = sub.add_parser("audit", help="Lê as bases e exibe os indicadores/achados.")
    audit_parser.add_argument("--json", action="store_true", help="Emite o relatório em JSON.")
    notify_parser = sub.add_parser("notify", help="Gera um resumo e opcionalmente envia ao GChat.")
    notify_parser.add_argument("--send", action="store_true", help="Confirma o envio ao webhook configurado.")
    notify_parser.add_argument("--thread-key", default="", help="Agrupa a mensagem em uma thread do GChat.")
    notify_parser.add_argument("--force", action="store_true", help="Reenvia alertas mesmo sem mudança desde o último envio.")
    notify_parser.add_argument("--initial", action="store_true", help="Publica a mensagem inicial de apresentação.")
    notify_parser.add_argument("--validation", action="store_true", help="Publica a mensagem de validação com as pendências atuais.")
    notify_parser.add_argument("--rules", default="", help="Regras separadas por vírgula para este ciclo de alerta.")
    notify_parser.add_argument("--schedule", action="store_true", help="Aplica a seleção diária ou de terça/quinta do agendamento do host.")
    report_parser = sub.add_parser("report", help="Gera o relatório gerencial de tarefas, projetos e menções.")
    report_parser.add_argument("--send", action="store_true", help="Envia o relatório ao webhook gerencial configurado.")
    report_parser.add_argument("--thread-key", default=MANAGEMENT_THREAD_KEY, help="Agrupa o relatório em uma thread do GChat.")
    sub.add_parser("snapshot", help="Executa a auditoria e salva um baseline JSON local.")
    run_parser = sub.add_parser("run", help="Executa uma coleta única e publica alertas/relatório opcionalmente.")
    run_parser.add_argument("--send", action="store_true", help="Envia alertas e relatório aos destinos configurados.")
    run_parser.add_argument("--thread-key", default="", help="Thread dos alertas; o relatório usa sua própria thread.")
    run_parser.add_argument("--schedule", action="store_true", help="Aplica as regras do calendário operacional.")
    sub.add_parser("doctor", help="Valida configuração local sem consultar o Notion nem enviar mensagens.")
    args = parser.parse_args()
    settings = Settings.from_environment()
    if args.command == "doctor":
        required = {
            "NOTION_TOKEN": settings.notion_token,
            "NOTION_TASKS_DATA_SOURCE_ID": settings.tasks_id,
            "NOTION_PROJECTS_DATA_SOURCE_ID": settings.projects_id,
            "NOTION_COLTEC_DATA_SOURCE_ID": settings.coltec_id,
            "NOTION_REQUESTS_DATA_SOURCE_ID": settings.requests_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            print("Configuração incompleta: " + ", ".join(missing))
            return 2
        print("Configuração local válida; nenhuma consulta ou publicação foi realizada.")
        return 0
    report = run_audit(settings)
    if args.command == "audit":
        if args.json:
            print(json.dumps(asdict(report), ensure_ascii=False, default=str, indent=2))
        else:
            print(render_markdown(report))
        return 0
    if args.command == "report":
        message = render_management_report(report, settings.manager_id)
        print(message)
        if args.send:
            if not report.complete:
                print("Relatório não enviado: a coleta está incompleta.")
                return 2
            messages = split_management_report(message)
            for part in messages:
                send_webhook(settings.gchat_gerencial_webhook_url, part, thread_key=args.thread_key, env_name="GCHAT_GERENCIAL_WEBHOOK_URL", payload=build_visual_payload(part, settings.gchat_project_logo_url, "Relatório gerencial — Gestão de Projetos", "management_report"))
            print(f"{len(messages)} mensagem(ns) do relatório gerencial enviada(s) ao Google Chat.")
    elif args.command == "snapshot":
        path = save_snapshot(report, settings.snapshot_dir, run_id=report.run_id)
        print(f"Snapshot salvo em {path}.")
    elif args.command == "run":
        print(render_markdown(report))
        if args.send:
            if not report.complete:
                print("Alertas e relatório não enviados: a coleta está incompleta.")
                return 2
            thread_key = args.thread_key or DEFAULT_THREAD_KEY
            def publish_with_category(message: str, key: str, category: str) -> None:
                for part in split_management_report(message):
                    send_webhook(settings.gchat_webhook_url, part, thread_key=key, payload=build_visual_payload(part, settings.gchat_project_logo_url, "Alerta — Gestão de Projetos", category))
            run_rules = scheduled_rules(datetime.now().weekday()) if args.schedule else None
            sent = send_pending_alerts(report, Path(settings.gchat_alert_state_file), lambda message, key: publish_with_category(message, key, "general"), thread_key=thread_key, rules=run_rules, send_with_category=publish_with_category)
            management = render_management_report(report, settings.manager_id)
            parts = split_management_report(management)
            for part in parts:
                send_webhook(settings.gchat_gerencial_webhook_url, part, thread_key=MANAGEMENT_THREAD_KEY, env_name="GCHAT_GERENCIAL_WEBHOOK_URL", payload=build_visual_payload(part, settings.gchat_project_logo_url, "Relatório gerencial — Gestão de Projetos", "management_report"))
            print(f"Run {report.run_id}: {len(sent)} alerta(s) e {len(parts)} parte(s) do relatório enviados.")
    else:
        rules = {rule.strip() for rule in args.rules.split(",") if rule.strip()} or None
        if args.schedule:
            rules = scheduled_rules(datetime.now().weekday())
        alerts = pending_alerts(report, rules=rules)
        if not alerts:
            print("Nenhuma pendência acionável no escopo da equipe de Integrações.")
        else:
            for alert in alerts:
                print(alert.message)
                print()
        if args.command == "notify" and args.send:
            if not report.complete:
                print("Alertas não enviados: a coleta está incompleta.")
                return 2
            def publish(message: str, thread_key: str) -> None:
                publish_with_category(message, thread_key, "general")

            def publish_with_category(message: str, thread_key: str, category: str) -> None:
                for part in split_management_report(message):
                    send_webhook(settings.gchat_webhook_url, part, thread_key=args.thread_key or thread_key or DEFAULT_THREAD_KEY, payload=build_visual_payload(part, settings.gchat_project_logo_url, "Alerta — Gestão de Projetos", category))

            published = 0
            thread_key = args.thread_key or DEFAULT_THREAD_KEY
            if args.initial:
                publish(INTRO_MESSAGE, thread_key)
                published += 1
            if args.validation:
                publish(validation_message(report), thread_key)
                published += 1
            if not args.initial and not args.validation:
                sent = send_pending_alerts(report, Path(settings.gchat_alert_state_file), publish, force=args.force, thread_key=thread_key, rules=rules, send_with_category=publish_with_category)
                published = len(sent)
            print(f"{published} mensagem(ns)/alerta(s) enviado(s) ao Google Chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
