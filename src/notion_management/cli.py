import argparse
import json
from datetime import datetime
from dataclasses import asdict
from pathlib import Path

from .alerting import DEFAULT_THREAD_KEY, INTRO_MESSAGE, pending_alerts, scheduled_rules, send_pending_alerts, validation_message
from .config import Settings
from .gchat import send_webhook
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
    sub.add_parser("snapshot", help="Executa a auditoria e salva um baseline JSON local.")
    args = parser.parse_args()
    settings = Settings.from_environment()
    report = run_audit(settings)
    if args.command == "snapshot":
        path = save_snapshot(report, settings.snapshot_dir)
        print(f"Snapshot salvo em {path}.")
    elif args.command == "audit" and args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, default=str, indent=2))
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
            def publish(message: str, thread_key: str) -> None:
                send_webhook(settings.gchat_webhook_url, message, thread_key=args.thread_key or thread_key or DEFAULT_THREAD_KEY)

            published = 0
            thread_key = args.thread_key or DEFAULT_THREAD_KEY
            if args.initial:
                publish(INTRO_MESSAGE, thread_key)
                published += 1
            if args.validation:
                publish(validation_message(report), thread_key)
                published += 1
            if not args.initial and not args.validation:
                sent = send_pending_alerts(report, Path(settings.gchat_alert_state_file), publish, force=args.force, thread_key=thread_key, rules=rules)
                published = len(sent)
            print(f"{published} mensagem(ns)/alerta(s) enviado(s) ao Google Chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
