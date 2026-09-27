# metacurate

Curate a metadata catalog into a list tailored to a specific use case, using
a pluggable [System One model](https://en.wikipedia.org/wiki/Jev_(AI_model)).

Given a catalog of items (each just an id plus a bag of metadata) and a
description of a use case, `metacurate` asks a System One model to score
each item's fit — e.g. "which help-center articles should show up for a new
admin setting up their team?" — and ranks the results by returned
probability.

## Install

```bash
pip install -e ".[dev]"
```

`SystemOneModel` needs a `SystemOneClient` for whichever System One model
you bring — see [Model backends](docs/model-backends.md) for the
ready-to-use `LayaClient` (requires Node.js 20+ and `npm install
@receptron/laya`) or wiring up your own.

## Usage

### Try it in 30 seconds, no model to install

`CurationModel` is just an interface — anything that returns `(id, rationale)`
pairs works, so you can see the whole `Catalog` → `Curator` pipeline run with
a trivial keyword matcher and nothing else to install:

```python
from metacurate import Catalog, Curator

class KeywordModel:
    def curate(self, items, use_case, limit):
        matches = [item for item in items if use_case.lower() in str(item.metadata).lower()]
        return [(item.id, "keyword match") for item in matches[:limit]]

catalog = Catalog.from_json("examples/articles.json")
curator = Curator(model=KeywordModel())
for result in curator.curate(catalog, "onboarding", limit=3):
    print(result.item.id, "-", result.rationale)
```

### Curate with a real System One model

The CLI, web app, and `SystemOneModel` all use an actual model's judgment
instead of keyword matching — by default, `LayaClient` (requires Node.js 20+
and `npm install @receptron/laya`; see [Model backends](docs/model-backends.md)):

```bash
metacurate examples/articles.json "onboarding a new team admin" -n 3
```

```python
from metacurate import Catalog, Curator
from metacurate.laya import LayaClient
from metacurate.models import SystemOneModel

catalog = Catalog.from_json("examples/articles.json")
curator = Curator(model=SystemOneModel(client=LayaClient()))
for result in curator.curate(catalog, "onboarding a new team admin", limit=3):
    print(result.item.id, "-", result.rationale)
```

## Design

- `Catalog` / `CatalogItem` — load metadata from JSON, CSV, or Excel; each
  item is just an `id` and a `dict` of metadata, no fixed schema.
- `CurationModel` — the interface any model backend implements: given the
  catalog items and a use case, return `(id, rationale)` pairs. `SystemOneModel`
  is the built-in implementation; swap in any other model, or a non-LLM
  system, by implementing the same interface.
- `Curator` — orchestrates loading a catalog and a model into a curated,
  justified list.
- `SystemOneModel` — bring your own System One model (TypeSafe's Jev, an
  open alternative like `LayaClient`, or a backend of your own) through the
  `SystemOneClient.ask_noul` seam.

See [`docs/`](docs/) for the full picture: [architecture](docs/architecture.md),
[catalog formats](docs/catalog-formats.md), [model backends](docs/model-backends.md)
(including how to wire up `SystemOneModel`/`LayaClient` or write your own),
and [CLI and web app usage](docs/cli-and-web.md).

## Tests

```bash
pytest
```
