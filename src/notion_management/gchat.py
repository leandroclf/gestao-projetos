import html
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .brand import PROJECT_NAME


def _inline_html(text: str) -> str:
    value = html.escape(text)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"(?<![\"=])(https?://[^\s<]+)", r'<a href="\1">\1</a>', value)
    return re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", value)


def _card_html(text: str, category: str = "general") -> str:
    """Renderiza texto usando as cores nativas e adaptativas do Google Chat.

    Cards enviados por webhook são exibidos tanto em temas claros quanto
    escuros, mas não recebem o tema do usuário como dado de entrada. Portanto,
    uma cor HTML fixa pode ficar ilegível em um dos temas. A categoria é
    mantida na assinatura para compatibilidade com os chamadores; a semântica
    continua explícita no texto e a hierarquia visual usa negrito e o cabeçalho.
    """
    del category
    return "<br>".join(_inline_html(line) for line in text.splitlines())


def build_visual_payload(
    message: str,
    logo_url: str = "",
    title: str = PROJECT_NAME,
    category: str = "general",
) -> dict:
    """Monta uma mensagem com texto de fallback e card visual para o Google Chat."""
    blocks = message.split("\n\n")
    header_text = blocks[0].replace("*", "") if blocks else title
    widgets: list[dict] = []
    for block in blocks:
        if not block.strip():
            continue
        widgets.append({"textParagraph": {"text": _card_html(block, category)}})
        urls = re.findall(r"https?://[^\s)]+", block)
        if urls:
            widgets.append({"buttonList": {"buttons": [{
                "text": "Abrir no Notion" if "notion.so" in urls[0] else "Abrir link",
                "onClick": {"openLink": {"url": urls[0].rstrip(".,")}},
            }]}})
    header = {"title": title, "subtitle": header_text}
    if logo_url:
        header.update({"imageUrl": logo_url, "imageType": "CIRCLE", "imageAltText": "Logo do projeto"})
    return {
        "cardsV2": [{"cardId": "gestao-projetos", "card": {"header": header, "sections": [{"widgets": widgets}]}}],
    }


def send_webhook(webhook_url: str, message: str, thread_key: str = "", timeout: int = 20, env_name: str = "GCHAT_WEBHOOK_URL", payload: dict | None = None) -> None:
    if not webhook_url:
        raise RuntimeError(f"{env_name} não configurado.")
    if thread_key:
        parts = urlsplit(webhook_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["threadKey"] = thread_key
        webhook_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    request = Request(
        webhook_url,
        data=json.dumps(payload or {"text": message}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout):
        return
