# CLI and web app

Both front ends wrap the same `Catalog` → `Curator` → `AnthropicModel` flow
(see [architecture.md](architecture.md)); neither currently exposes
`SystemOneModel`/`LayaClient` as a runtime option — wire those up in code if
you want them (see [model-backends.md](model-backends.md)).

## CLI — `metacurate`

```bash
metacurate <catalog-file> "<use case>" [-n LIMIT] [-m MODEL]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `catalog` (positional) | — | Path to a `.json` or `.csv` catalog file |
| `use_case` (positional) | — | Free-text description of who/what you're curating for |
| `-n`, `--limit` | `10` | Max items to return |
| `-m`, `--model` | `claude-sonnet-5` | Anthropic model name to curate with |

```bash
metacurate examples/articles.json "onboarding a new team admin" -n 3
```

Output is a ranked, 1-indexed list of `id — rationale` lines. Requires
`ANTHROPIC_API_KEY` in the environment (`AnthropicModel`'s default client
reads it via the `anthropic` SDK).

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
is how tests substitute a fake model instead of calling the real Anthropic
API; use the same hook to run the web app against `SystemOneModel` or any
other backend:

```python
from metacurate.webapp import create_app
from metacurate.models import SystemOneModel

app = create_app(model=SystemOneModel(client=YourClient()))
app.run(debug=True, port=5000)
```
