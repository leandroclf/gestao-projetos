import html
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .brand import PROJECT_NAME, semantic_color


def _card_html(text: str, category: str = "general") -> str:
    value = html.escape(text)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"(?<![\"=])(https?://[^\s<]+)", r'<a href="\1">\1</a>', value)
    value = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", value)
    value = value.replace("\n", "<br>")
    return f'<font color="{semantic_color(category)}">{value}</font>' if category != "general" else value


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
        "text": message,
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
