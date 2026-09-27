import json
import subprocess
from unittest.mock import patch

import pytest

from metacurate.jev_laya import LayaClient
from metacurate.models import NoulQuestion


def _completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def test_ask_noul_sends_state_and_questions_and_parses_answers():
    questions = [
        NoulQuestion(id="a", statement="Item 'a' is a strong match"),
        NoulQuestion(id="b", statement="Item 'b' is a strong match"),
    ]
    client = LayaClient()

    with patch("metacurate.jev_laya.subprocess.run") as run:
        run.return_value = _completed(
            json.dumps({"answers": [{"id": "a", "probability": 0.8}, {"id": "b", "probability": 0.3}]})
        )
        answers = client.ask_noul('[{"id": "a"}, {"id": "b"}]', questions)

    sent_payload = json.loads(run.call_args.kwargs["input"])
    assert sent_payload["state"] == [{"id": "a"}, {"id": "b"}]
    assert sent_payload["questions"] == [
        {"id": "a", "statement": "Item 'a' is a strong match"},
        {"id": "b", "statement": "Item 'b' is a strong match"},
    ]
    assert [(a.id, a.probability) for a in answers] == [("a", 0.8), ("b", 0.3)]


def test_ask_noul_passes_through_non_json_state_unparsed():
    client = LayaClient()

    with patch("metacurate.jev_laya.subprocess.run") as run:
        run.return_value = _completed(json.dumps({"answers": []}))
        client.ask_noul("not json", [])

    sent_payload = json.loads(run.call_args.kwargs["input"])
    assert sent_payload["state"] == "not json"


def test_ask_noul_raises_when_node_is_missing():
    client = LayaClient(node_bin="definitely-not-a-real-binary")

    with patch("metacurate.jev_laya.subprocess.run", side_effect=FileNotFoundError()):
        with pytest.raises(RuntimeError, match="Node.js"):
            client.ask_noul("{}", [])


def test_ask_noul_raises_with_stderr_on_bridge_failure():
    client = LayaClient()
    error = subprocess.CalledProcessError(1, cmd=[], stderr="boom")

    with patch("metacurate.jev_laya.subprocess.run", side_effect=error):
        with pytest.raises(RuntimeError, match="boom"):
            client.ask_noul("{}", [])
