# Model backends

Every backend implements `CurationModel.curate(items, use_case, limit) ->
list[tuple[str, str]]` (see [architecture.md](architecture.md)). This page
covers the ones metacurate ships, and how to add your own.

## `SystemOneModel` and `SystemOneClient` — bring your own System One model

"System One" names a class of models that answer typed questions
(`Choice`, `Score`, `Noul`) against a block of shared state in a single
parallel pass, returning calibrated probabilities instead of free text.
TypeSafe's Jev is one such model (see `JevClient` below); open alternatives
exist too (see `LayaClient` below).

`SystemOneModel` asks one `Noul` question per catalog item — *"is this item
a strong match for the use case?"* — against the whole catalog as shared
state in one request, then ranks items by the returned probability. It
doesn't talk to any particular backend directly; it takes a
`SystemOneClient`:

```python
class SystemOneClient(Protocol):
    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        ...
```

To bring your own backend, implement `ask_noul`: turn `state` (a JSON string
of the catalog) and `questions` (one `NoulQuestion(id, statement)` per item)
into whatever request shape your model expects, and return one
`NoulAnswer(id, probability)` per question. `tests/test_models.py`'s
`FakeSystemOneClient` shows the minimal shape; `metacurate.laya.LayaClient`
shows a real one.

```python
from metacurate.models import SystemOneModel

curator = Curator(model=SystemOneModel(client=YourClient()))
```

## `JevClient` — a ready-made `SystemOneClient` for TypeSafe's Jev

`metacurate.jev.JevClient`

Talks to TypeSafe's Jev over the real API, via the official
[`typesafe-sdk`](https://github.com/typesafe-ai/typesafe-sdk-python) package.

**Requirements**: `pip install metacurate[jev]` (or `pip install
typesafe-sdk` directly), and a `TYPESAFE_API_KEY` in the environment.
`JevClient` doesn't read the key itself — it constructs a `TypeSafeClient`
with whatever keyword arguments you pass through, and that SDK resolves
`api_key`, `base_url`, `default_model`, and `timeout` from its own
constructor arguments or the matching `TYPESAFE_*` environment variables,
exactly as the official client does.

**How it works**: one `Noul` question per catalog item, batched into a
single `system_one` request keyed by item id — the same shape
`SystemOneModel` already builds — then `NoulAnswer`s are read back off
`result.nouls[item_id].noul`.

```python
from metacurate.jev import JevClient
from metacurate.models import SystemOneModel

curator = Curator(model=SystemOneModel(client=JevClient()))
```

Pass constructor keyword arguments straight through to `TypeSafeClient`,
e.g. `JevClient(model="jev-1.13.0", timeout=30.0)`.

**Catalogs too large for one request**: Jev caps how many tokens (state +
questions) fit in a single `system_one` call. `JevClient` handles this
itself — on `max_tokens_exceeded` it splits the batch in half and retries
each half (recursively, so it converges on however many requests actually
fit), narrowing `state` to just each half's own items so the retry is
actually smaller, not just fewer questions over the same state. This is
transparent: a 130-item catalog that fails outright in one request still
returns a single, correctly-ranked result — just via a few requests under
the hood instead of one. Only a single item whose own metadata (plus the
use case text) exceeds the limit on its own raises a `ValueError` naming
that item, since there's nothing left to split.

**Errors**: a missing `typesafe-sdk` install raises `RuntimeError` with
install instructions; a single item too large to fit even alone raises
`ValueError`; everything else (auth, rate limits, connectivity) surfaces
as the SDK's own typed exceptions (`TypeSafeAuthenticationError`,
`TypeSafeRateLimitError`, `TypeSafeAPIConnectionError`, etc.).

## `LayaClient` — a ready-made `SystemOneClient`

`metacurate.laya.LayaClient`

Backed by [Laya](https://github.com/receptron/laya), an open-source,
Jev-compatible System One model that runs locally via ONNX Runtime — useful
if you don't have Jev access yet, or want a self-hosted backend.

**Requirements**: Node.js 20+ on the machine running metacurate, and
`npm install @receptron/laya`. The model's ONNX weights (~1.7GB) auto-download
from Hugging Face the first time it's used, and are cached afterward.

**How it works**: Laya ships as a Node.js/TypeScript package, not a Python
one, so `LayaClient` doesn't bind to it in-process. Instead:

1. `LayaClient.ask_noul` serializes `{state, questions}` to JSON.
2. It runs `node src/metacurate/laya_bridge.mjs`, piping that JSON to stdin.
3. The bridge script loads Laya, asks all questions as `noul` primitives in
   one batched `systemOne()` call, and writes `{answers: [...]}` JSON to
   stdout.
4. `LayaClient` parses that back into `NoulAnswer` objects.

```python
from metacurate.laya import LayaClient
from metacurate.models import SystemOneModel

curator = Curator(model=SystemOneModel(client=LayaClient()))
```

**Configuration**: `LayaClient(node_bin="node", script=None, timeout=300.0)`
— override `node_bin` if `node` isn't on `PATH` under that name, or `timeout`
(seconds) if scoring a large catalog takes longer than the default 5 minutes
(the first call also pays for the one-time model download).

**Errors**: a missing `node` binary or a non-zero exit from the bridge
script both raise `RuntimeError` with the underlying cause (a "Node.js not
found" message, or the bridge's stderr), rather than failing silently.

## Writing a non-System-One `CurationModel`

`CurationModel` doesn't require a System One model at all — an LLM, a rules engine, a
cached lookup, or a human review queue all qualify as long as `curate`
returns `(id, rationale)` pairs:

```python
class KeywordModel:
    def curate(self, items, use_case, limit):
        matches = [item for item in items if use_case.lower() in str(item.metadata).lower()]
        return [(item.id, "keyword match") for item in matches[:limit]]
```
