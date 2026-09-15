import json
import random
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class NotionApiError(RuntimeError):
    pass


class NotionClient:
    def __init__(self, token: str, version: str = "2025-09-03", timeout: int = 30, max_attempts: int = 5) -> None:
        self.base_url = "https://api.notion.com/v1"
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": version,
            "Content-Type": "application/json",
        }

    def query_data_source(self, data_source_id: str) -> list[dict]:
        rows: list[dict] = []
        cursor: str | None = None
        while True:
            payload: dict[str, str | int] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            response = self._request("POST", f"/data_sources/{data_source_id}/query", payload)
            rows.extend(response.get("results", []))
            if not response.get("has_more"):
                return rows
            cursor = response.get("next_cursor")
            if not cursor:
                return rows

    def list_comments(self, block_id: str) -> list[dict]:
        comments: list[dict] = []
        cursor: str | None = None
        while True:
            query = f"?block_id={block_id}"
            if cursor:
                query += f"&start_cursor={cursor}"
            response = self._request("GET", f"/comments{query}", None)
            comments.extend(response.get("results", []))
            if not response.get("has_more") or not response.get("next_cursor"):
                return comments
            cursor = response["next_cursor"]

    def list_block_children(self, block_id: str) -> list[dict]:
        blocks: list[dict] = []
        cursor: str | None = None
        while True:
            query = "?page_size=100"
            if cursor:
                query += f"&start_cursor={cursor}"
            response = self._request("GET", f"/blocks/{block_id}/children{query}", None)
            blocks.extend(response.get("results", []))
            if not response.get("has_more") or not response.get("next_cursor"):
                return blocks
            cursor = response["next_cursor"]

    def _request(self, method: str, path: str, payload: dict | None) -> dict:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers=self.headers,
            method=method,
        )
        for attempt in range(self.max_attempts):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                retryable = exc.code in {429, 529} or (method == "GET" and exc.code in {500, 502, 503, 504}) or (method == "POST" and path.endswith("/query") and exc.code in {500, 502, 503, 504})
                if not retryable or attempt == self.max_attempts - 1:
                    detail = exc.read().decode("utf-8", errors="replace")
                    raise NotionApiError(f"Falha na API do Notion (HTTP {exc.code}): {detail}") from exc
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = max(0.0, float(retry_after)) if retry_after is not None else min(2 ** attempt, 30)
                except ValueError:
                    delay = min(2 ** attempt, 30)
                time.sleep(delay + random.uniform(0, 0.25))
            except URLError as exc:
                if attempt == self.max_attempts - 1:
                    raise NotionApiError(f"Falha na API do Notion: {exc}") from exc
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 0.25))
