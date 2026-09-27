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

- `Catalog` / `CatalogItem` — load metadata from JSON or CSV; each item is
  just an `id` and a `dict` of metadata, no fixed schema.
- `CurationModel` — the interface any model backend implements: given the
  catalog items and a use case, return `(id, rationale)` pairs. `AnthropicModel`
  is the built-in implementation; swap in any other model, or a
  non-LLM system, by implementing the same interface.
- `Curator` — orchestrates loading a catalog and a model into a curated,
  justified list.

## Tests

```bash
pytest
```
