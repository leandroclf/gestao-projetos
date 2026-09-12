import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .models import AuditReport


def save_snapshot(report: AuditReport, directory: str, today: date | None = None) -> Path:
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{(today or date.today()).isoformat()}.json"
    target.write_text(json.dumps(asdict(report), ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    return target

