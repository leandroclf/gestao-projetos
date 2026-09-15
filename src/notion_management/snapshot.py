import json
from dataclasses import asdict
from datetime import date
from uuid import uuid4
from pathlib import Path

from .models import AuditReport


def save_snapshot(report: AuditReport, directory: str, today: date | None = None, run_id: str | None = None) -> Path:
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_id or report.run_id
    filename = f"{(today or date.today()).isoformat()}-{run_id or uuid4().hex}.json" if run_id else f"{(today or date.today()).isoformat()}.json"
    target = target_dir / filename
    target.write_text(json.dumps(asdict(report), ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    return target
