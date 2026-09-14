import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def send_webhook(webhook_url: str, message: str, thread_key: str = "", timeout: int = 20, env_name: str = "GCHAT_WEBHOOK_URL") -> None:
    if not webhook_url:
        raise RuntimeError(f"{env_name} não configurado.")
    if thread_key:
        parts = urlsplit(webhook_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["threadKey"] = thread_key
        webhook_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    request = Request(
        webhook_url,
        data=json.dumps({"text": message}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout):
        return
