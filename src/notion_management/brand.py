"""Tokens e regras visuais da comunicação digital da HivePlace."""

BRAND_NAME = "HIVEPlace"
PROJECT_NAME = "Gestão de Projetos"
BRAND_POSITIONING = "A primeira agência de interoperabilidade do Brasil."

# Paleta oficial consolidada nos materiais de identidade visual.
COLORS = {
    "black": "#0D0D0E",
    "brown_dark": "#332528",
    "gold": "#EFB41B",
    "gold_dark": "#D98E06",
    "brown": "#5D2E07",
    "brown_black": "#1A1214",
    "graphite": "#1A1A1C",
    "gray": "#404146",
    "white": "#EEF1F0",
}

# Cores semânticas são deliberadamente separadas da identidade institucional.
SEMANTIC_COLORS = {
    "general": COLORS["graphite"],
    "overdue": "#B3261E",
    "blocked": COLORS["brown"],
    "approval": COLORS["gold_dark"],
    "stale": COLORS["gold_dark"],
    "customer_demand": COLORS["gold"],
    "coltec": COLORS["brown_dark"],
    "agenda": COLORS["gold_dark"],
    "mention": COLORS["brown_dark"],
    # O Google Chat usa fundo claro no card; texto institucional deve manter
    # contraste, deixando o dourado apenas para destaques pontuais.
    "management_report": COLORS["graphite"],
    "completed": "#137333",
}


def semantic_color(category: str) -> str:
    """Retorna a cor semântica conhecida, com fallback neutro."""
    return SEMANTIC_COLORS.get(category, SEMANTIC_COLORS["general"])
