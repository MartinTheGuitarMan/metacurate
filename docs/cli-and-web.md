# CLI and web app

Both front ends wrap the same `Catalog` → `Curator` → `SystemOneModel` flow
(see [architecture.md](architecture.md)), defaulting to `LayaClient` as the
`SystemOneClient` — swap in a different one in code if you want it (see
[model-backends.md](model-backends.md)).

## CLI — `metacurate`

```bash
metacurate <catalog-file> "<use case>" [-n LIMIT]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `catalog` (positional) | — | Path to a `.json` or `.csv` catalog file |
| `use_case` (positional) | — | Free-text description of who/what you're curating for |
| `-n`, `--limit` | `10` | Max items to return |

```bash
metacurate examples/articles.json "onboarding a new team admin" -n 3
```

Output is a ranked, 1-indexed list of `id — rationale` lines. Requires
Node.js 20+ and `npm install @receptron/laya` on the machine running
metacurate (see [model-backends.md](model-backends.md#layaclient--a-ready-made-systemoneclient)).

Note the CLI infers JSON vs. CSV from the file extension and doesn't accept
`.xlsx` — use the web app or `Catalog.from_excel(...)` directly for Excel
catalogs.

## Web app — `metacurate-web`

```bash
pip install -e ".[web]"
metacurate-web
```

Starts a Flask dev server on `http://localhost:5000` (`create_app().run(debug=True,
port=5000)` — debug mode, not for production use as-is). The page
(`src/metacurate/templates/index.html`) accepts:

- a catalog file upload (`.csv`, `.json`, or `.xlsx`, capped at 10MB by
  `MAX_CONTENT_LENGTH`)
- a use case question
- a result limit

and renders the same ranked `id — rationale` results, or an error message
for an empty file, unsupported extension, or missing input.

`create_app(model=None)` takes an optional `CurationModel` override — this
is how tests substitute a fake model instead of calling the real
`LayaClient`; use the same hook to run the web app against a different
`SystemOneClient`, or a different `CurationModel` entirely:

```python
from metacurate.webapp import create_app
from metacurate.models import SystemOneModel

app = create_app(model=SystemOneModel(client=YourClient()))
app.run(debug=True, port=5000)
```
