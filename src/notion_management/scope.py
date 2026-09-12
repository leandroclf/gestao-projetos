from .config import Settings
from .models import Record


def _compact(value: str) -> str:
    return value.replace("-", "").lower()


def in_scope(record: Record, settings: Settings) -> bool:
    """Aplica o mesmo recorte gerencial definido nos painéis do Notion."""
    area_match = _compact(record.area_id) == _compact(settings.integrations_area_id)
    owner_match = _compact(record.owner_id) in {_compact(settings.manager_id), *(_compact(item) for item in settings.team_member_ids)}
    if record.source in {"tasks", "projects"}:
        return area_match or owner_match
    if record.source == "coltec":
        return record.area == "Integração" or _compact(record.owner_id) == _compact(settings.manager_id)
    if record.source == "requests":
        return record.request_team == "HIVEPlace" or _compact(record.owner_id) == _compact(settings.manager_id)
    return False
