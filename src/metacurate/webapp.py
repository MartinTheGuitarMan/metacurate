from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, Response, render_template, request

from .catalog import Catalog
from .curator import Curator
from .models import CurationModel, SystemOneModel

ALLOWED_EXTENSIONS = {".csv", ".json", ".xlsx"}


def _default_model() -> CurationModel:
    """The SystemOneClient to use when no model override is passed to create_app.

    Set METACURATE_MODEL=laya to use the open-source LayaClient instead;
    defaults to JevClient (requires `pip install metacurate[jev]` and
    TYPESAFE_API_KEY).
    """
    backend = os.environ.get("METACURATE_MODEL", "jev").strip().lower()
    if backend == "laya":
        from .laya import LayaClient

        return SystemOneModel(client=LayaClient())
    from .jev import JevClient

    return SystemOneModel(client=JevClient())


def create_app(model: CurationModel | None = None) -> Flask:
    """Build the Flask app. Pass `model` to override the default SystemOneModel (e.g. in tests)."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    def get_model() -> CurationModel:
        return model if model is not None else _default_model()

    password = os.environ.get("WEBAPP_PASSWORD", "")
    username = os.environ.get("WEBAPP_USERNAME", "metacurate")

    @app.before_request
    def require_auth():
        if not password:
            return None  # no WEBAPP_PASSWORD set: auth disabled (local dev)
        auth = request.authorization
        valid = (
            auth is not None
            and secrets.compare_digest(auth.username, username)
            and secrets.compare_digest(auth.password, password)
        )
        if not valid:
            return Response(
                "Authentication required", 401, {"WWW-Authenticate": 'Basic realm="metacurate"'}
            )
        return None

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            return render_template("index.html", error=None, results=None, question=None, limit=None)

        file = request.files.get("catalog")
        question = request.form.get("question", "").strip()
        limit_raw = request.form.get("limit", "10")

        error = None
        results = None

        if not file or not file.filename:
            error = "Choose a CSV, Excel, or JSON file."
        elif not question:
            error = "Enter a question."
        else:
            suffix = Path(file.filename).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                error = f"Unsupported file type '{suffix}'. Use .csv, .xlsx, or .json."
            else:
                try:
                    limit = int(limit_raw)
                except ValueError:
                    limit = 10
                try:
                    catalog = _load_catalog(file, suffix)
                    if len(catalog) == 0:
                        raise ValueError("That file has no rows.")
                    results = Curator(model=get_model()).curate(catalog, question, limit=limit)
                except Exception as exc:  # noqa: BLE001 - surfaced to the user, not a crash
                    error = str(exc)

        return render_template(
            "index.html", error=error, results=results, question=question, limit=limit_raw
        )

    return app


def _load_catalog(file, suffix: str) -> Catalog:
    if suffix == ".csv":
        return Catalog.from_csv_text(file.read().decode("utf-8"))
    if suffix == ".json":
        return Catalog.from_json_text(file.read().decode("utf-8"))
    return Catalog.from_excel_bytes(file.read())


app = create_app()  # module-level instance for WSGI servers, e.g. `gunicorn metacurate.webapp:app`


def main() -> None:
    app.run(debug=True, port=5000)


if __name__ == "__main__":
    main()
