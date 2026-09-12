import argparse
import json
from dataclasses import asdict

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
        message = render_markdown(report)
        print(message)
        if args.command == "notify" and args.send:
            send_webhook(settings.gchat_webhook_url, message, thread_key=args.thread_key)
            print("Resumo enviado ao Google Chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
