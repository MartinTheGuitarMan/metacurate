from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template, request

from .catalog import Catalog
from .curator import Curator
from .laya import LayaClient
from .models import CurationModel, SystemOneModel

ALLOWED_EXTENSIONS = {".csv", ".json", ".xlsx"}


def create_app(model: CurationModel | None = None) -> Flask:
    """Build the Flask app. Pass `model` to override the default SystemOneModel (e.g. in tests)."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    def get_model() -> CurationModel:
        return model if model is not None else SystemOneModel(client=LayaClient())

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            return render_template("index.html")

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


def main() -> None:
    create_app().run(debug=True, port=5000)


if __name__ == "__main__":
    main()
