import io
import json
import unittest
from email.message import Message
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from notion_management.notion_api import NotionApiError, NotionClient


def _http_error(code: int, headers: dict | None = None, body: str = "") -> HTTPError:
    hdrs = Message()
    for key, value in (headers or {}).items():
        hdrs[key] = value
    return HTTPError("https://api.notion.com/v1/x", code, "erro", hdrs, io.BytesIO(body.encode("utf-8")))


class _FakeResponse:
    """Imita o objeto retornado por urlopen, usável como context manager."""

    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _response(payload: dict) -> _FakeResponse:
    return _FakeResponse(payload)


class NotionApiTest(unittest.TestCase):
    def test_query_data_source_follows_pagination_until_has_more_is_false(self) -> None:
        client = NotionClient("token")
        responses = [
            _response({"results": [{"id": "1"}], "has_more": True, "next_cursor": "c2"}),
            _response({"results": [{"id": "2"}], "has_more": False}),
        ]
        with patch("notion_management.notion_api.urlopen", side_effect=responses):
            rows = client.query_data_source("source-1")
        self.assertEqual(["1", "2"], [row["id"] for row in rows])

    def test_retries_on_429_and_honors_retry_after_header(self) -> None:
        client = NotionClient("token", max_attempts=3)
        with patch("notion_management.notion_api.urlopen", side_effect=[_http_error(429, {"Retry-After": "0"}), _response({"results": [], "has_more": False})]), \
                patch("notion_management.notion_api.time.sleep") as sleep:
            rows = client.query_data_source("source-1")
        self.assertEqual([], rows)
        sleep.assert_called_once()

    def test_non_retryable_error_raises_immediately_without_sleep(self) -> None:
        client = NotionClient("token", max_attempts=5)
        with patch("notion_management.notion_api.urlopen", side_effect=[_http_error(404, body="não encontrado")]), \
                patch("notion_management.notion_api.time.sleep") as sleep:
            with self.assertRaises(NotionApiError):
                client.query_data_source("source-1")
        sleep.assert_not_called()

    def test_exhausts_attempts_on_persistent_server_error(self) -> None:
        client = NotionClient("token", max_attempts=2)
        with patch("notion_management.notion_api.urlopen", side_effect=[_http_error(503), _http_error(503)]), \
                patch("notion_management.notion_api.time.sleep"):
            with self.assertRaises(NotionApiError):
                client.query_data_source("source-1")

    def test_retries_on_connection_error_then_succeeds(self) -> None:
        client = NotionClient("token", max_attempts=2)
        with patch("notion_management.notion_api.urlopen", side_effect=[URLError("timeout"), _response({"results": [], "has_more": False})]), \
                patch("notion_management.notion_api.time.sleep"):
            rows = client.query_data_source("source-1")
        self.assertEqual([], rows)

    def test_list_comments_stops_when_next_cursor_is_missing_despite_has_more(self) -> None:
        client = NotionClient("token")
        with patch("notion_management.notion_api.urlopen", side_effect=[_response({"results": [{"id": "c1"}], "has_more": True})]):
            comments = client.list_comments("block-1")
        self.assertEqual(["c1"], [comment["id"] for comment in comments])


if __name__ == "__main__":
    unittest.main()
