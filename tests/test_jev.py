import json
import sys
import types

from metacurate.models import ChoiceQuestion, NoulQuestion


class FakeTypeSafeBadRequestError(Exception):
    pass


_MAX_TOKENS_ERROR = FakeTypeSafeBadRequestError(
    'POST https://api.typesafe.ai/v1/systemone: 400 '
    '{"detail":{"error_type":"max_tokens_exceeded"}} (request_id=req_test)'
)


def _install_fake_typesafe_sdk(system_one_calls, max_tokens_threshold=None, other_error=None):
    """Register a fake `typesafe_sdk` module so JevClient's lazy import resolves
    to test doubles instead of the real SDK.

    - `other_error`: if set, every call raises this (for non-max-tokens errors).
    - `max_tokens_threshold`: if set, a call raises the fake max_tokens_exceeded
      error whenever it's asked more than this many questions at once —
      simulating a request-size wall a caller can work around by splitting.
    - Otherwise every call succeeds with a fake 0.5 probability per question.
    """

    class FakeNoul:
        def __init__(self, instructions):
            self.instructions = instructions

    class FakeNoulAnswer:
        def __init__(self, noul):
            self.noul = noul

    class FakeChoice:
        def __init__(self, instructions, criteria):
            self.instructions = instructions
            self.criteria = criteria

    class FakeChoiceAnswer:
        def __init__(self, choice, confidence):
            self.choice = choice
            self.confidence = confidence

    class FakeSystemOneResponse:
        def __init__(self, nouls=None, choices=None):
            self.nouls = nouls or {}
            self.choices = choices or {}

    class FakeTypeSafeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def system_one(self, *, state, questions):
            system_one_calls.append({"state": state, "questions": dict(questions)})
            if other_error is not None:
                raise other_error
            if max_tokens_threshold is not None and len(questions) > max_tokens_threshold:
                raise _MAX_TOKENS_ERROR
            nouls, choices = {}, {}
            for qid, q in questions.items():
                if isinstance(q, FakeChoice):
                    choices[qid] = FakeChoiceAnswer(choice=next(iter(q.criteria)), confidence=0.9)
                else:
                    nouls[qid] = FakeNoulAnswer(noul=0.5)
            return FakeSystemOneResponse(nouls=nouls, choices=choices)

        def close(self):
            pass

    module = types.ModuleType("typesafe_sdk")
    module.Noul = FakeNoul
    module.Choice = FakeChoice
    module.TypeSafeClient = FakeTypeSafeClient
    module.TypeSafeBadRequestError = FakeTypeSafeBadRequestError
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


def test_jev_client_splits_batch_on_max_tokens_exceeded_and_merges_results():
    calls = []
    _install_fake_typesafe_sdk(calls, max_tokens_threshold=2)  # >2 questions fails
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()
    items = [{"id": qid, "name": f"item {qid}"} for qid in "abcd"]
    questions = [NoulQuestion(id=qid, statement=f"q about {qid}") for qid in "abcd"]

    answers = client.ask_noul(json.dumps(items), questions)

    assert {a.id for a in answers} == {"a", "b", "c", "d"}
    assert all(a.probability == 0.5 for a in answers)

    # First call attempted all 4 and failed; then two successful calls of 2 each.
    sizes = [len(c["questions"]) for c in calls]
    assert sizes == [4, 2, 2]

    # Each successful sub-call's state was narrowed to just its own items,
    # not the full original 4-item state.
    successful = calls[1:]
    for call in successful:
        state_ids = {entry["id"] for entry in call["state"]}
        assert state_ids == set(call["questions"])
        assert len(state_ids) == 2


def test_jev_client_raises_friendly_error_when_single_item_still_too_large():
    calls = []
    _install_fake_typesafe_sdk(calls, max_tokens_threshold=0)  # even 1 question fails
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()
    questions = [NoulQuestion(id="a", statement="q"), NoulQuestion(id="b", statement="q")]

    try:
        client.ask_noul('[{"id": "a"}, {"id": "b"}]', questions)
        raised = None
    except ValueError as exc:
        raised = str(exc)

    assert raised is not None
    assert "alone is too large" in raised
    assert "api.typesafe.ai" not in raised  # friendly message, not the raw SDK error


def test_jev_client_reraises_other_bad_request_errors_unchanged():
    error = FakeTypeSafeBadRequestError("400 {\"detail\":{\"error_type\":\"invalid_model\"}}")
    _install_fake_typesafe_sdk([], other_error=error)
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()

    try:
        client.ask_noul("{}", [NoulQuestion(id="a", statement="q")])
        raised = None
    except FakeTypeSafeBadRequestError as exc:
        raised = exc

    assert raised is error


def test_jev_client_sends_one_choice_question_per_item():
    calls = []
    _install_fake_typesafe_sdk(calls)
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()
    questions = [
        ChoiceQuestion(id="a", statement="Which category fits 'a'?", options=["X", "Y"]),
        ChoiceQuestion(id="b", statement="Which category fits 'b'?", options=["X", "Y"]),
    ]

    answers = client.ask_choice('[{"id": "a"}, {"id": "b"}]', questions)

    assert len(calls) == 1
    sent = calls[0]["questions"]
    assert set(sent) == {"a", "b"}
    assert sent["a"].instructions == "Which category fits 'a'?"
    assert sent["a"].criteria == {"X": None, "Y": None}
    assert {a.id for a in answers} == {"a", "b"}
    assert all(a.choice == "X" for a in answers)  # fake always picks the first option
    assert all(a.confidence == 0.9 for a in answers)


def test_jev_client_splits_choice_batch_on_max_tokens_exceeded_and_merges_results():
    calls = []
    _install_fake_typesafe_sdk(calls, max_tokens_threshold=2)
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()
    items = [{"id": qid, "name": f"item {qid}"} for qid in "abcd"]
    questions = [
        ChoiceQuestion(id=qid, statement=f"q about {qid}", options=["X", "Y"]) for qid in "abcd"
    ]

    answers = client.ask_choice(json.dumps(items), questions)

    assert {a.id for a in answers} == {"a", "b", "c", "d"}
    sizes = [len(c["questions"]) for c in calls]
    assert sizes == [4, 2, 2]


def test_jev_client_choice_and_noul_share_the_same_max_tokens_error_message():
    calls = []
    _install_fake_typesafe_sdk(calls, max_tokens_threshold=0)
    sys.modules.pop("metacurate.jev", None)
    from metacurate.jev import JevClient

    client = JevClient()
    questions = [
        ChoiceQuestion(id="a", statement="q", options=["X"]),
        ChoiceQuestion(id="b", statement="q", options=["X"]),
    ]

    try:
        client.ask_choice('[{"id": "a"}, {"id": "b"}]', questions)
        raised = None
    except ValueError as exc:
        raised = str(exc)

    assert raised is not None
    assert "alone is too large" in raised
