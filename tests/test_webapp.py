import base64
import io

from metacurate.webapp import _display_title, create_app


class FakeModel:
    def curate(self, items, use_case, limit):
        return [(item.id, f"matches '{use_case}'") for item in items[:limit]]


def _basic_auth_header(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_display_title_picks_name_field_case_insensitively():
    assert _display_title({"Name": "Alpha", "tag": "x"}) == "Alpha"


def test_display_title_falls_back_through_preference_order():
    assert _display_title({"title": "Beta", "label": "Gamma"}) == "Beta"
    assert _display_title({"label": "Gamma"}) == "Gamma"


def test_display_title_skips_empty_values():
    assert _display_title({"name": "", "label": "Gamma"}) == "Gamma"


def test_display_title_returns_none_when_no_title_field():
    assert _display_title({"vessel_type": "Chemical Tanker"}) is None


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


def test_csv_upload_strips_bom_from_first_column_name():
    # No "id" column, so the BOM-prefixed first column is treated as metadata,
    # same shape as the real report: {'﻿VesselTimeseriesId': ...}.
    client = create_app(model=FakeModel()).test_client()
    data = {
        "catalog": (io.BytesIO("VesselId,Name\nv1,Alpha\n".encode("utf-8-sig")), "catalog.csv"),
        "question": "demo",
    }
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"<dt>VesselId</dt>" in response.data
    assert "﻿VesselId".encode() not in response.data


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


def test_no_auth_required_when_password_env_unset(monkeypatch):
    monkeypatch.delenv("WEBAPP_PASSWORD", raising=False)
    client = create_app(model=FakeModel()).test_client()
    response = client.get("/")
    assert response.status_code == 200


def test_missing_credentials_rejected_when_password_set(monkeypatch):
    monkeypatch.setenv("WEBAPP_PASSWORD", "secret")
    client = create_app(model=FakeModel()).test_client()
    response = client.get("/")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Basic")


def test_wrong_credentials_rejected_when_password_set(monkeypatch):
    monkeypatch.setenv("WEBAPP_PASSWORD", "secret")
    client = create_app(model=FakeModel()).test_client()
    response = client.get("/", headers=_basic_auth_header("metacurate", "wrong"))
    assert response.status_code == 401


def test_correct_credentials_accepted_when_password_set(monkeypatch):
    monkeypatch.setenv("WEBAPP_PASSWORD", "secret")
    client = create_app(model=FakeModel()).test_client()
    response = client.get("/", headers=_basic_auth_header("metacurate", "secret"))
    assert response.status_code == 200


def test_custom_username_respected(monkeypatch):
    monkeypatch.setenv("WEBAPP_PASSWORD", "secret")
    monkeypatch.setenv("WEBAPP_USERNAME", "admin")
    client = create_app(model=FakeModel()).test_client()
    response = client.get("/", headers=_basic_auth_header("admin", "secret"))
    assert response.status_code == 200


class ProbabilityModel:
    def curate(self, items, use_case, limit):
        return [(item.id, "match probability 0.87") for item in items[:limit]]


def test_probability_rationale_renders_as_percentage_meter():
    client = create_app(model=ProbabilityModel()).test_client()
    data = {"catalog": (io.BytesIO(b"id,name\na,Alpha\n"), "catalog.csv"), "question": "demo"}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"87%" in response.data
    assert b"match probability 0.87" not in response.data  # replaced by the meter, not shown raw


def test_non_probability_rationale_renders_as_plain_text():
    client = create_app(model=FakeModel()).test_client()
    data = {"catalog": (io.BytesIO(b"id,name\na,Alpha\n"), "catalog.csv"), "question": "demo"}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"matches &#39;demo&#39;" in response.data or b"matches 'demo'" in response.data


def test_metadata_renders_as_key_value_list_not_raw_dict():
    client = create_app(model=FakeModel()).test_client()
    data = {"catalog": (io.BytesIO(b"id,name\na,Alpha\n"), "catalog.csv"), "question": "demo"}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b"{&#39;name&#39;: &#39;Alpha&#39;}" not in response.data  # not a raw dict repr
    assert b"<dt>name</dt>" in response.data
    assert b"<dd>Alpha</dd>" in response.data


def test_metadata_summary_shows_a_title_when_a_name_field_is_present():
    client = create_app(model=FakeModel()).test_client()
    data = {
        "catalog": (io.BytesIO(b"id,name,tag\na,Alpha,x\n"), "catalog.csv"),
        "question": "demo",
    }
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b'<span class="meta-title">Alpha</span>' in response.data
    assert b"2 fields" in response.data  # name + tag


def test_metadata_summary_falls_back_to_field_count_without_a_title_field():
    client = create_app(model=FakeModel()).test_client()
    data = {
        "catalog": (io.BytesIO(b"id,vessel_type\na,Chemical Tanker\n"), "catalog.csv"),
        "question": "demo",
    }
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert b'class="meta-title"' not in response.data
    assert b"1 field<" in response.data
