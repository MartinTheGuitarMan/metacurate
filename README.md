# metacurate

Curate a metadata catalog into a list tailored to a specific use case, using
a pluggable AI model.

Given a catalog of items (each just an id plus a bag of metadata) and a
description of a use case, `metacurate` asks a model to pick and justify the
most relevant subset — e.g. "which help-center articles should show up for a
new admin setting up their team?"

## Install

```bash
pip install -e ".[anthropic,dev]"
export ANTHROPIC_API_KEY=...
```

## Usage

```bash
metacurate examples/articles.json "onboarding a new team admin" -n 3
```

```python
from metacurate import Catalog, Curator
from metacurate.models import AnthropicModel

catalog = Catalog.from_json("examples/articles.json")
curator = Curator(model=AnthropicModel())
for result in curator.curate(catalog, "onboarding a new team admin", limit=3):
    print(result.item.id, "-", result.rationale)
```

## Design

- `Catalog` / `CatalogItem` — load metadata from JSON, CSV, or Excel; each
  item is just an `id` and a `dict` of metadata, no fixed schema.
- `CurationModel` — the interface any model backend implements: given the
  catalog items and a use case, return `(id, rationale)` pairs. `AnthropicModel`
  is the built-in implementation; swap in any other model, or a
  non-LLM system, by implementing the same interface.
- `Curator` — orchestrates loading a catalog and a model into a curated,
  justified list.

### Model backends

- **`AnthropicModel`** — asks Claude to pick and justify the top `limit`
  items in one prompt; the response is free-text JSON.
- **`SystemOneModel`** — bring your own [System One
  model](https://en.wikipedia.org/wiki/Jev_(AI_model)): TypeSafe's Jev, an
  open alternative like Laya, or a backend of your own. A System One request
  pairs a block of state with one or more typed questions ("primitives":
  `Choice`, `Score`, `Noul`) evaluated together in a single parallel pass,
  returning structured answers instead of free text. `SystemOneModel` asks
  one `Noul` question per catalog item — *"is this item a strong match for
  the use case?"* — against the whole catalog as shared state, and ranks
  items by the returned probability. The seam is `SystemOneClient.ask_noul(state,
  questions)`: implement it against whichever backend you have access to and
  hand it to `SystemOneModel`; see `tests/test_models.py` for a fake client
  illustrating the shape, and `LayaClient` below for a real one.
- **`LayaClient`** (`metacurate.laya`) — a `SystemOneClient` backed by
  [Laya](https://github.com/receptron/laya), an open-source, Jev-compatible
  System One model that runs locally via ONNX Runtime — handy if you're
  waiting on Jev access, or just don't want a proprietary dependency. Laya
  ships as an npm package, so `LayaClient` shells out to a bundled Node.js
  bridge script rather than binding to it directly. Requires Node.js 20+ and
  `npm install @receptron/laya` (its ~1.7GB ONNX weights auto-download from
  Hugging Face on first use):

  ```python
  from metacurate.laya import LayaClient
  from metacurate.models import SystemOneModel

  curator = Curator(model=SystemOneModel(client=LayaClient()))
  ```

  Swap in Jev or another backend later with no other code changes.

## Tests

```bash
pytest
```
