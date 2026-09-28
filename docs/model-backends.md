# Model backends

Every backend implements `CurationModel.curate(items, use_case, limit) ->
list[tuple[str, str]]` (see [architecture.md](architecture.md)). This page
covers the ones metacurate ships, and how to add your own.

## `SystemOneModel` and `SystemOneClient` — bring your own System One model

"System One" names a class of models that answer typed questions
(`Choice`, `Score`, `Noul`) against a block of shared state in a single
parallel pass, returning calibrated probabilities instead of free text.
TypeSafe's Jev is one such model; open alternatives exist too (see
`LayaClient` below).

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

## `JevClient` — a ready-made `SystemOneClient`

`metacurate.jev.JevClient`

Calls TypeSafe's Jev directly, via the official `typesafe-sdk` package.

**Requirements**: `pip install metacurate[jev]` (or `pip install typesafe-sdk`
directly), and a Jev API key from https://console.typesafe.ai.

**Configuration**: `JevClient(api_key=None, model=None, timeout=60.0)` — with
no `api_key`, it reads the `TYPESAFE_API_KEY` environment variable, matching
the official SDK's convention. `model` overrides the SDK's default model
alias (e.g. to pin a specific Jev version); `timeout` is seconds per request.

```python
from metacurate.jev import JevClient
from metacurate.models import SystemOneModel

curator = Curator(model=SystemOneModel(client=JevClient()))
```

**Errors**: a missing `typesafe-sdk` install, a missing/empty API key, and
any failure from the underlying API call all raise `RuntimeError` with the
underlying cause, rather than failing silently.

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
