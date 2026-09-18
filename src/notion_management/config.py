import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Carrega pares simples do .env sem executar o arquivo como shell."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    notion_token: str
    notion_version: str
    gchat_webhook_url: str
    gchat_gerencial_webhook_url: str
    tasks_id: str
    projects_id: str
    coltec_id: str
    requests_id: str
    integrations_area_id: str
    manager_id: str
    team_member_ids: tuple[str, ...]
    snapshot_dir: str
    gchat_alert_state_file: str = "reports/gchat-alert-state.json"
    gchat_project_logo_url: str = ""

    @classmethod
    def from_environment(cls) -> "Settings":
        _load_dotenv()
        return cls(
            notion_token=os.environ.get("NOTION_TOKEN", ""),
            notion_version=os.environ.get("NOTION_VERSION", "2025-09-03"),
            gchat_webhook_url=os.environ.get("GCHAT_WEBHOOK_URL", ""),
            gchat_gerencial_webhook_url=os.environ.get("GCHAT_GERENCIAL_WEBHOOK_URL", ""),
            gchat_project_logo_url=os.environ.get("GCHAT_PROJECT_LOGO_URL", ""),
            tasks_id=os.environ.get("NOTION_TASKS_DATA_SOURCE_ID", ""),
            projects_id=os.environ.get("NOTION_PROJECTS_DATA_SOURCE_ID", ""),
            coltec_id=os.environ.get("NOTION_COLTEC_DATA_SOURCE_ID", ""),
            requests_id=os.environ.get("NOTION_REQUESTS_DATA_SOURCE_ID", ""),
            integrations_area_id=os.environ.get("NOTION_INTEGRATIONS_AREA_ID", ""),
            manager_id=os.environ.get("NOTION_MANAGER_ID", ""),
            team_member_ids=tuple(filter(None, os.environ.get("NOTION_TEAM_MEMBER_IDS", "").split(","))),
            snapshot_dir=os.environ.get("NOTION_SNAPSHOT_DIR", "reports/snapshots"),
            gchat_alert_state_file=os.environ.get("GCHAT_ALERT_STATE_FILE", "reports/gchat-alert-state.json"),
        )

    def require_notion_token(self) -> None:
        if not self.notion_token:
            raise RuntimeError("NOTION_TOKEN não configurado. Preencha a variável de ambiente antes da execução.")
