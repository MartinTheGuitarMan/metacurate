import sys
import types

from metacurate.models import NoulQuestion


def _install_fake_typesafe_sdk(system_one_calls):
    """Register a fake `typesafe_sdk` module so JevClient's lazy import resolves
    to test doubles instead of the real SDK.
    """

    class FakeNoul:
        def __init__(self, instructions):
            self.instructions = instructions

    class FakeNoulAnswer:
        def __init__(self, noul):
            self.noul = noul

    class FakeSystemOneResponse:
        def __init__(self, nouls):
            self.nouls = nouls

    class FakeTypeSafeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def system_one(self, *, state, questions):
            system_one_calls.append({"state": state, "questions": questions})
            return FakeSystemOneResponse(
                {qid: FakeNoulAnswer(noul=0.5) for qid in questions}
            )

        def close(self):
            pass

    module = types.ModuleType("typesafe_sdk")
    module.Noul = FakeNoul
    module.TypeSafeClient = FakeTypeSafeClient
    sys.modules["typesafe_sdk"] = module
    return module


def test_jev_client_sends_one_noul_question_per_item(monkeypatch):
    calls = []
    _install_fake_typesafe_sdk(calls)
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()
    questions = [
        NoulQuestion(id="a", statement="Item 'a' is a strong match"),
        NoulQuestion(id="b", statement="Item 'b' is a strong match"),
    ]

    answers = client.ask_noul('{"items": ["a", "b"]}', questions)

    assert len(calls) == 1
    sent_questions = calls[0]["questions"]
    assert set(sent_questions) == {"a", "b"}
    assert sent_questions["a"].instructions == "Item 'a' is a strong match"
    assert calls[0]["state"] == {"items": ["a", "b"]}
    assert {a.id for a in answers} == {"a", "b"}
    assert all(a.probability == 0.5 for a in answers)


def test_jev_client_passes_non_json_state_through_unparsed():
    calls = []
    _install_fake_typesafe_sdk(calls)
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()
    client.ask_noul("not json", [NoulQuestion(id="a", statement="q")])

    assert calls[0]["state"] == "not json"


def test_jev_client_missing_sdk_raises_runtime_error(monkeypatch, capsys):
    # Simulate `typesafe_sdk` not being installed by making its import fail,
    # without touching sys.path or importing the real (untrusted) package.
    sys.modules.pop("typesafe_sdk", None)
    sys.modules.pop("metacurate.jev", None)
    import builtins

    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "typesafe_sdk":
            raise ImportError("no module named typesafe_sdk")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    from metacurate.jev import JevClient

    try:
        JevClient()
        raised = False
    except RuntimeError as exc:
        raised = "typesafe-sdk" in str(exc)

    assert raised
