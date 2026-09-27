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
- **`JevModel`** — targets [Jev](https://en.wikipedia.org/wiki/Jev_(AI_model)),
  TypeSafe's structured-answer model. A Jev request pairs a block of state
  with one or more typed questions ("primitives": `Choice`, `Score`, `Noul`)
  evaluated together in a single parallel pass, returning structured answers
  instead of free text. `JevModel` asks one `Noul` question per catalog item
  — *"is this item a strong match for the use case?"* — against the whole
  catalog as shared state, and ranks items by the returned probability.
  TypeSafe hasn't published Jev's request/response format or SDK, so
  `JevModel` takes a `client` implementing `JevClient.ask_noul(state,
  questions)` — that's the seam to wire up the real SDK once you have access
  to it; see `tests/test_models.py` for a fake client illustrating the shape.

## Tests

```bash
pytest
```
