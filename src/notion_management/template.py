from typing import Any


TASK_SECTIONS = ("motivação e contexto", "critério de pronto", "anotações")
PROJECT_SECTIONS = (
    "motivação e contexto",
    "definição de pronto e de sucesso",
    "aspectos críticos e condições de contorno",
    "outros pontos relevantes",
    "tarefas e desenvolvimento",
)


def _plain_text(block: dict[str, Any]) -> str:
    data = block.get(block.get("type", ""), {})
    parts = data.get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in parts).strip()


def missing_sections(source: str, properties: dict[str, Any], blocks: list[dict[str, Any]]) -> tuple[str, ...]:
    headings = {_plain_text(block).casefold() for block in blocks if block.get("type", "").startswith("heading_")}
    required = TASK_SECTIONS if source == "tasks" else PROJECT_SECTIONS
    missing = [section.title() for section in required if section not in headings]
    if source == "projects":
        description = properties.get("Descrição", {})
        text = "".join(item.get("plain_text", "") for item in description.get("rich_text", [])).strip()
        if not text:
            missing.insert(0, "Descrição")
    return tuple(missing)
