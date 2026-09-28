import sys
import types
from unittest.mock import MagicMock

import pytest

from metacurate.jev import JevClient
from metacurate.models import NoulQuestion


class _FakeTypeSafeClient:
    """Records the kwargs it's constructed and called with; last instance wins."""

    instances: list["_FakeTypeSafeClient"] = []
    system_one_return = None
    system_one_error = None

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.call_kwargs = None
        _FakeTypeSafeClient.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def system_one(self, **kwargs):
        self.call_kwargs = kwargs
        if _FakeTypeSafeClient.system_one_error is not None:
            raise _FakeTypeSafeClient.system_one_error
        return _FakeTypeSafeClient.system_one_return


class _Noul:
    def __init__(self, instructions):
        self.instructions = instructions


def _response(nouls):
    response = MagicMock()
    response.nouls = {qid: MagicMock(noul=prob) for qid, prob in nouls.items()}
    return response


@pytest.fixture(autouse=True)
def fake_sdk_module(monkeypatch):
    _FakeTypeSafeClient.instances = []
    _FakeTypeSafeClient.system_one_return = _response({})
    _FakeTypeSafeClient.system_one_error = None

    module = types.ModuleType("typesafe_sdk")
    module.Noul = _Noul
    module.TypeSafeClient = _FakeTypeSafeClient
    monkeypatch.setitem(sys.modules, "typesafe_sdk", module)
    return module


def test_ask_noul_sends_state_and_questions_and_parses_answers():
    questions = [
        NoulQuestion(id="a", statement="Item 'a' is a strong match"),
        NoulQuestion(id="b", statement="Item 'b' is a strong match"),
    ]
    _FakeTypeSafeClient.system_one_return = _response({"a": 0.8, "b": 0.3})
    client = JevClient(api_key="test-key")

    answers = client.ask_noul('[{"id": "a"}, {"id": "b"}]', questions)

    assert [(a.id, a.probability) for a in answers] == [("a", 0.8), ("b", 0.3)]
    instance = _FakeTypeSafeClient.instances[-1]
    assert instance.call_kwargs["state"] == [{"id": "a"}, {"id": "b"}]
    assert set(instance.call_kwargs["questions"].keys()) == {"a", "b"}
    assert instance.call_kwargs["questions"]["a"].instructions == "Item 'a' is a strong match"


def test_ask_noul_passes_through_non_json_state_unparsed():
    client = JevClient(api_key="test-key")

    client.ask_noul("not json", [])

    instance = _FakeTypeSafeClient.instances[-1]
    assert instance.call_kwargs["state"] == "not json"


def test_client_uses_provided_api_key():
    client = JevClient(api_key="test-key")

    client.ask_noul("{}", [])

    assert _FakeTypeSafeClient.instances[-1].init_kwargs["api_key"] == "test-key"


def test_reads_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "env-key")
    client = JevClient()

    assert client._api_key == "env-key"

    client.ask_noul("{}", [])

    assert _FakeTypeSafeClient.instances[-1].init_kwargs["api_key"] == "env-key"


def test_ask_noul_raises_when_sdk_not_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "typesafe_sdk", None)
    client = JevClient(api_key="test-key")

    with pytest.raises(RuntimeError, match="typesafe-sdk not installed"):
        client.ask_noul("{}", [])


def test_ask_noul_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    client = JevClient(api_key=None)

    with pytest.raises(RuntimeError, match="No Jev API key found"):
        client.ask_noul("{}", [])


def test_ask_noul_wraps_sdk_errors():
    _FakeTypeSafeClient.system_one_error = ValueError("rate limited")
    client = JevClient(api_key="test-key")

    with pytest.raises(RuntimeError, match="Jev API call failed"):
        client.ask_noul("{}", [])
