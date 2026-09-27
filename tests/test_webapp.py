import io

from metacurate.webapp import create_app


class FakeModel:
    def curate(self, items, use_case, limit):
        return [(item.id, f"matches '{use_case}'") for item in items[:limit]]


def test_get_index_renders_form():
    client = create_app(model=FakeModel()).test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"metacurate" in response.data


def test_get_index_shows_no_results_or_error_before_any_submission():
    client = create_app(model=FakeModel()).test_client()
    response = client.get("/")
    assert b"No matches found" not in response.data
    assert b'<div class="error">' not in response.data


def test_missing_file_shows_error():
    client = create_app(model=FakeModel()).test_client()
    response = client.post("/", data={"question": "demo"})
    assert b"Choose a CSV" in response.data


def test_missing_question_shows_error():
    client = create_app(model=FakeModel()).test_client()
    data = {"catalog": (io.BytesIO(b"id,name\na,Alpha\n"), "catalog.csv")}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"Enter a question" in response.data


def test_unsupported_extension_shows_error():
    client = create_app(model=FakeModel()).test_client()
    data = {"catalog": (io.BytesIO(b"hello"), "catalog.txt"), "question": "demo"}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"Unsupported file type" in response.data


def test_csv_upload_returns_ranked_results_respecting_limit():
    client = create_app(model=FakeModel()).test_client()
    data = {
        "catalog": (io.BytesIO(b"id,name\na,Alpha\nb,Beta\n"), "catalog.csv"),
        "question": "demo use case",
        "limit": "1",
    }
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert b"Alpha" in response.data
    assert b"Beta" not in response.data


def test_json_upload_returns_ranked_results():
    client = create_app(model=FakeModel()).test_client()
    catalog_json = b'[{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}]'
    data = {"catalog": (io.BytesIO(catalog_json), "catalog.json"), "question": "demo"}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"Alpha" in response.data
    assert b"Beta" in response.data


def test_xlsx_upload_returns_ranked_results():
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["id", "name"])
    sheet.append(["a", "Alpha"])
    sheet.append(["b", "Beta"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    client = create_app(model=FakeModel()).test_client()
    data = {"catalog": (buffer, "catalog.xlsx"), "question": "demo"}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"Alpha" in response.data
    assert b"Beta" in response.data


def test_empty_catalog_shows_error():
    client = create_app(model=FakeModel()).test_client()
    data = {"catalog": (io.BytesIO(b"[]"), "catalog.json"), "question": "demo"}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"no rows" in response.data
