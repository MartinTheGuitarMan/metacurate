# Architecture

metacurate has three moving pieces, each independent of the others:

```
Catalog  ──items──▶  Curator  ◀──picks──  CurationModel
(load)                (orchestrate)        (AnthropicModel / SystemOneModel / your own)
```

## `Catalog` and `CatalogItem`

`src/metacurate/catalog.py`

A `CatalogItem` is just an `id: str` plus a `metadata: dict[str, str]` — no
fixed schema, so any tabular or JSON data works without a mapping layer.
`Catalog` loads a list of these from JSON, CSV, or Excel (`from_json`,
`from_csv`, `from_excel`, and their `_text`/`_bytes` variants for in-memory
data such as an uploaded file). If a row has an `id` column/key it's used;
otherwise items are numbered by position.

## `CurationModel`

`src/metacurate/models.py`

The one interface every model backend implements:

```python
def curate(self, items: list[CatalogItem], use_case: str, limit: int) -> list[tuple[str, str]]:
    """Return up to `limit` (item_id, rationale) pairs, most relevant first."""
```

metacurate ships two implementations — `AnthropicModel` and `SystemOneModel`
(see [model-backends.md](model-backends.md)) — but the interface is the
extension point: a non-LLM system (a rules engine, a human review queue, a
cached lookup) is a valid `CurationModel` as long as it returns
`(id, rationale)` pairs.

## `Curator`

`src/metacurate/curator.py`

`Curator.curate(catalog, use_case, limit)` is the orchestration step: it
hands the model the catalog's items and use case, then resolves the model's
`(id, rationale)` picks back against the original `CatalogItem`s (dropping
any id the model returns that isn't in the catalog) and wraps each into a
`CurationResult(item, rationale)`.

## Front ends

`cli.py` and `webapp.py` are both thin wrappers around this same
`Catalog` → `Curator` → `CurationModel` flow — see
[cli-and-web.md](cli-and-web.md).
