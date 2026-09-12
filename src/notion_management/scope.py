from .config import Settings
from .models import Record


def _compact(value: str) -> str:
    return value.replace("-", "").lower()


def _area_candidates(record: Record) -> tuple[str, ...]:
    if record.area_ids:
        return record.area_ids
    return (record.area_id,) if record.area_id else ()


def in_scope(record: Record, settings: Settings) -> bool:
    """Aplica o mesmo recorte gerencial definido nos painéis do Notion."""
    target_area = _compact(settings.integrations_area_id)
    area_match = any(_compact(area_id) == target_area for area_id in _area_candidates(record))
    owner_match = _compact(record.owner_id) in {_compact(settings.manager_id), *(_compact(item) for item in settings.team_member_ids)}
    if record.source in {"tasks", "projects"}:
        return area_match or owner_match
    if record.source == "coltec":
        return record.area == "Integração" or _compact(record.owner_id) == _compact(settings.manager_id)
    if record.source == "requests":
        return record.request_team == "HIVEPlace" or _compact(record.owner_id) == _compact(settings.manager_id)
    return False
