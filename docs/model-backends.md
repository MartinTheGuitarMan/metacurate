# Model backends

Every backend implements `CurationModel.curate(items, use_case, limit) ->
list[tuple[str, str]]` (see [architecture.md](architecture.md)). This page
covers the ones metacurate ships, and how to add your own.

## `SystemOneModel` and `SystemOneClient` — bring your own System One model

"System One" names a class of models that answer typed questions
(`Choice`, `Score`, `Noul`) against a block of shared state in a single
parallel pass, returning calibrated probabilities instead of free text.
TypeSafe's Jev is one such model; open alternatives exist too (see
`LayaClient` and `KevClient` below).

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
and `metacurate.kev.KevClient` show real ones.

```python
from metacurate.models import SystemOneModel

curator = Curator(model=SystemOneModel(client=YourClient()))
```

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

## `KevClient` — a lighter `SystemOneClient` for constrained hardware

`metacurate.kev.KevClient`

Backed by [Kev](https://github.com/jaredpalmer/kev) (weights at
[huggingface.co/jaredpalmer](https://huggingface.co/jaredpalmer)): a family
of small System One decision models — LoRA adapters plus a pointer head
over Qwen bases, from kev-0.5b up through kev-27b — that speak TypeSafe's
public `/v1/systemone` HTTP contract, the same one Jev implements. Useful
when Laya's ~1.7GB ONNX download and Node.js dependency are more than you
want, or when you're running on hardware too small for Jev-scale models.

**Sizing for a 16GB Apple Silicon Mac**: the 0.5b/0.6b/0.8b tier runs
comfortably there. Per Kev's own benchmarks, kev-0.6b is the documented
latency/accuracy sweet spot on Apple Silicon (0.12s per five-question
request vs 0.33s for kev-0.8b, at a modest accuracy cost); kev-0.5b trades
further accuracy for the smallest footprint. kev-4b and up have more
general knowledge but leave much less headroom on 16GB, since they carry a
full-size Qwen base rather than one under 1B parameters.

**How it works**: unlike Laya, Kev isn't embedded as a library — it's
served as its own local HTTP process that `KevClient` talks to over plain
HTTP (`urllib`, no new dependency):

```bash
uv run --extra serve python -m kev.serve --run jaredpalmer/kev-0.6b --port 8009
```

```python
from metacurate.kev import KevClient
from metacurate.models import SystemOneModel

curator = Curator(model=SystemOneModel(client=KevClient()))
```

`KevClient.ask_noul` POSTs `{state, model, questions}` to
`<base_url>/v1/systemone` (one `{"type": "noul", "instructions": ...}`
entry per question) and reads back `{answers: {id: {"noul": probability}}}`.

**Configuration**: `KevClient(base_url="http://127.0.0.1:8009",
model="kev-latest", timeout=30.0)` — `base_url` must match whichever
`--port` (and `--host`) you started `kev.serve` with; `model` is passed
through to the server, useful if one `kev.serve` process is serving
multiple checkpoints.

**Errors**: `RuntimeError` if the server can't be reached (with the
`kev.serve` command to start one) or if it responds with an HTTP error (with
the response body included).

## Classifying a single item instead of curating a catalog

`metacurate.classify.classify`

`SystemOneModel` answers "which of these catalog items fits this use
case?" — many items, one use case. Sometimes the question is the mirror
image: "which of these known labels does this one item match?" — one item,
many labels. That's a classification task (e.g. "which protocol is this
raw sample?"), and it reuses the exact same `SystemOneClient.ask_noul`
seam, just with the roles swapped:

```python
from metacurate.catalog import CatalogItem
from metacurate.classify import classify

labels = [
    CatalogItem(id="spam", metadata={"description": "unsolicited bulk email"}),
    CatalogItem(id="not_spam", metadata={"description": "a legitimate message"}),
]
ranked = classify(client, "raw item text", labels)  # [(label_id, probability), ...] most likely first
```

See [`examples/classify_protocol.py`](../examples/classify_protocol.py) for
a worked example: classifying raw maritime telemetry samples (an NMEA 0183
GGA line, an NMEA 0183 RMC line, a Modbus-style engine telemetry record) by
protocol/message type, using `KevClient` against `examples/protocol_labels.json`.

## Writing a non-System-One `CurationModel`

`CurationModel` doesn't require a System One model at all — an LLM, a rules
engine, a cached lookup, or a human review queue all qualify as long as `curate`
returns `(id, rationale)` pairs:

```python
class KeywordModel:
    def curate(self, items, use_case, limit):
        matches = [item for item in items if use_case.lower() in str(item.metadata).lower()]
        return [(item.id, "keyword match") for item in matches[:limit]]
```
