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
