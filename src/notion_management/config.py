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
    tasks_id: str
    projects_id: str
    coltec_id: str
    requests_id: str
    integrations_area_id: str
    manager_id: str
    team_member_ids: tuple[str, ...]
    snapshot_dir: str
    gchat_alert_state_file: str = "reports/gchat-alert-state.json"

    @classmethod
    def from_environment(cls) -> "Settings":
        _load_dotenv()
        return cls(
            notion_token=os.environ.get("NOTION_TOKEN", ""),
            notion_version=os.environ.get("NOTION_VERSION", "2025-09-03"),
            gchat_webhook_url=os.environ.get("GCHAT_WEBHOOK_URL", ""),
            tasks_id=os.environ.get("NOTION_TASKS_DATA_SOURCE_ID", "2f89821c-9b76-805f-bee2-000b71d2b012"),
            projects_id=os.environ.get("NOTION_PROJECTS_DATA_SOURCE_ID", "2a19821c-9b76-80c0-90f7-000b1b3a969c"),
            coltec_id=os.environ.get("NOTION_COLTEC_DATA_SOURCE_ID", "732a2bf4-d5d6-4f4d-83b0-918a919ce22d"),
            requests_id=os.environ.get("NOTION_REQUESTS_DATA_SOURCE_ID", "3049821c-9b76-8097-9d8e-000bf4cfd760"),
            integrations_area_id=os.environ.get("NOTION_INTEGRATIONS_AREA_ID", "2cf9821c-9b76-80e4-847d-ed513b60542c"),
            manager_id=os.environ.get("NOTION_MANAGER_ID", "2a8d872b-594c-8139-9dff-00025b218268"),
            team_member_ids=tuple(filter(None, os.environ.get(
                "NOTION_TEAM_MEMBER_IDS",
                "2f6d872b-594c-8161-ba5b-000220935468,372d872b-594c-8137-bb5d-0002057b7ea8,2fbd872b-594c-8134-a985-0002a8e31c7b,372d872b-594c-813f-a059-00028cf75c9c,2f6d872b-594c-8104-bfe1-0002056ed704,328d872b-594c-81a6-8b1b-00028f0bcee9",
            ).split(","))),
            snapshot_dir=os.environ.get("NOTION_SNAPSHOT_DIR", "reports/snapshots"),
            gchat_alert_state_file=os.environ.get("GCHAT_ALERT_STATE_FILE", "reports/gchat-alert-state.json"),
        )

    def require_notion_token(self) -> None:
        if not self.notion_token:
            raise RuntimeError("NOTION_TOKEN não configurado. Preencha a variável de ambiente antes da execução.")
