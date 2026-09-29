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
is how tests substitute a fake model instead of calling the real backend;
use the same hook to run the web app against a different `SystemOneClient`,
or a different `CurationModel` entirely:

```python
from metacurate.webapp import create_app
from metacurate.models import SystemOneModel

app = create_app(model=SystemOneModel(client=YourClient()))
app.run(debug=True, port=5000)
```

With no override, the web app picks its backend from the `METACURATE_MODEL`
env var: `jev` (default, requires `TYPESAFE_API_KEY`) or `laya`.

### Deploying it (password-protected)

The app gates every route behind HTTP Basic Auth when `WEBAPP_PASSWORD` is
set — leave it unset for local dev (no auth), set it for anything reachable
from the internet:

| Env var | Default | Meaning |
| --- | --- | --- |
| `WEBAPP_PASSWORD` | *(unset)* | Set this to require a password; unset disables auth entirely |
| `WEBAPP_USERNAME` | `metacurate` | Basic-auth username |
| `METACURATE_MODEL` | `jev` | `jev` or `laya` |
| `TYPESAFE_API_KEY` | — | Required when `METACURATE_MODEL=jev` |

`metacurate.webapp:app` is a module-level Flask instance for a real WSGI
server (`create_app().run(debug=True, ...)` is dev-only). Install with the
`deploy` extra (`pip install -e ".[deploy]"`, adds `gunicorn`), and run:

```bash
gunicorn -w 2 -b 0.0.0.0:$PORT metacurate.webapp:app
```

A `Procfile` with that same command, and a `render.yaml` blueprint, are
included at the repo root for one-click-ish deployment:

1. Push this repo to GitHub (already done if you're reading this from there).
2. On [Render](https://render.com), **New** → **Blueprint**, point it at the
   repo — it reads `render.yaml` and creates the service on the free tier.
3. Render prompts for the two secret env vars the blueprint leaves blank:
   `TYPESAFE_API_KEY` and `WEBAPP_PASSWORD`. Fill both in.
4. Deploy. You get an `https://<name>.onrender.com` URL, TLS included,
   gated behind the username/password you set.

Any other host that runs a `Procfile` or a plain `gunicorn` command
(Fly.io, Railway, a VPS, ...) works the same way — the app itself doesn't
know or care which one it's on.
