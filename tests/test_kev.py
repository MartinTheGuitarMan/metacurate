import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from metacurate.kev import KevClient
from metacurate.models import NoulQuestion


def _response(body: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(body).encode()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_ask_noul_sends_state_and_noul_questions_and_parses_answers():
    questions = [
        NoulQuestion(id="a", statement="Item 'a' is a strong match"),
        NoulQuestion(id="b", statement="Item 'b' is a strong match"),
    ]
    client = KevClient(base_url="http://127.0.0.1:8009/", model="kev-0.6b")

    with patch("metacurate.kev.urllib.request.urlopen") as urlopen:
        urlopen.return_value = _response(
            {"answers": {"a": {"type": "noul", "noul": 0.8}, "b": {"type": "noul", "noul": 0.3}}}
        )
        answers = client.ask_noul("raw sample text", questions)

    request = urlopen.call_args.args[0]
    sent_payload = json.loads(request.data)
    assert request.full_url == "http://127.0.0.1:8009/v1/systemone"
    assert sent_payload["state"] == "raw sample text"
    assert sent_payload["model"] == "kev-0.6b"
    assert sent_payload["questions"] == {
        "a": {"type": "noul", "instructions": "Item 'a' is a strong match"},
        "b": {"type": "noul", "instructions": "Item 'b' is a strong match"},
    }
    assert [(a.id, a.probability) for a in answers] == [("a", 0.8), ("b", 0.3)]


def test_ask_noul_raises_when_server_is_unreachable():
    client = KevClient()

    with patch(
        "metacurate.kev.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        with pytest.raises(RuntimeError, match="kev.serve"):
            client.ask_noul("state", [])


def test_ask_noul_raises_with_response_body_on_http_error():
    client = KevClient()
    error = urllib.error.HTTPError(
        url="http://127.0.0.1:8009/v1/systemone", code=500, msg="boom", hdrs=None, fp=None
    )
    error.read = lambda: b"internal error"

    with patch("metacurate.kev.urllib.request.urlopen", side_effect=error):
        with pytest.raises(RuntimeError, match="internal error"):
            client.ask_noul("state", [])
