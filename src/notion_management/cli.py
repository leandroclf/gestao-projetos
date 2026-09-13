import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .alerting import pending_alerts, send_pending_alerts
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
        alerts = pending_alerts(report)
        if not alerts:
            print("Nenhuma pendência acionável no escopo da equipe de Integrações.")
        else:
            for alert in alerts:
                print(alert.message)
                print()
        if args.command == "notify" and args.send:
            def publish(message: str, thread_key: str) -> None:
                send_webhook(settings.gchat_webhook_url, message, thread_key=args.thread_key or thread_key)

            sent = send_pending_alerts(report, Path(settings.gchat_alert_state_file), publish, force=args.force)
            print(f"{len(sent)} alerta(s) enviado(s) ao Google Chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
