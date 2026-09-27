import json

from metacurate.catalog import Catalog


def test_from_json(tmp_path):
    data = [
        {"id": "a", "name": "Alpha", "tag": "x"},
        {"id": "b", "name": "Beta", "tag": "y"},
    ]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data))

    catalog = Catalog.from_json(path)

    assert len(catalog) == 2
    assert catalog.items[0].id == "a"
    assert catalog.items[0].metadata == {"name": "Alpha", "tag": "x"}


def test_from_csv(tmp_path):
    path = tmp_path / "catalog.csv"
    path.write_text("id,name,tag\na,Alpha,x\nb,Beta,y\n")

    catalog = Catalog.from_csv(path)

    assert len(catalog) == 2
    assert catalog.items[1].id == "b"
    assert catalog.items[1].metadata == {"name": "Beta", "tag": "y"}


def test_from_json_without_id_uses_row_index():
    catalog = Catalog.from_json_text('[{"name": "Alpha"}, {"name": "Beta"}]')
    assert [item.id for item in catalog.items] == ["0", "1"]


def test_from_csv_without_id_uses_row_index():
    catalog = Catalog.from_csv_text("name\nAlpha\nBeta\n")
    assert [item.id for item in catalog.items] == ["0", "1"]


def test_from_excel(tmp_path):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["id", "name", "tag"])
    sheet.append(["a", "Alpha", "x"])
    sheet.append(["b", "Beta", "y"])
    path = tmp_path / "catalog.xlsx"
    workbook.save(path)

    catalog = Catalog.from_excel(path)

    assert len(catalog) == 2
    assert catalog.items[0].id == "a"
    assert catalog.items[0].metadata == {"name": "Alpha", "tag": "x"}
