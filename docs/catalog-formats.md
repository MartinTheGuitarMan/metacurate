# Catalog formats

`Catalog` loads a list of `CatalogItem`s from JSON, CSV, or Excel. In every
format, an `id` column/key becomes `CatalogItem.id`; everything else on the
row becomes `CatalogItem.metadata`. Rows without an `id` are numbered by
position (`"0"`, `"1"`, ...).

## JSON

An array of flat objects. See `examples/articles.json`:

```json
[
  {"id": "onboarding-101", "title": "Getting started with your account", "tags": "onboarding,setup"},
  {"id": "billing-faq", "title": "Billing and invoices FAQ", "tags": "billing,support"}
]
```

```python
Catalog.from_json("examples/articles.json")
Catalog.from_json_text(json_string)  # e.g. an uploaded file's contents
```

## CSV

A header row plus data rows, read with `csv.DictReader`. See
`examples/vessels.csv`. All values come back as strings — metacurate never
interprets metadata types, it just hands them to the model as text.

```python
Catalog.from_csv("examples/vessels.csv")
Catalog.from_csv_text(csv_string)
```

## Excel

The first worksheet's first row is read as headers; remaining rows become
items (via `openpyxl`, an optional dependency — see `pip install -e ".[web]"`
or `".[dev]"`). Empty cells become `""`.

```python
Catalog.from_excel("examples/vessels.xlsx")
Catalog.from_excel_bytes(file_bytes)
```

## Choosing a use case description

The use case is a free-text string handed to whichever `CurationModel` you
use (e.g. `"onboarding a new team admin"`). There's no required format —
write it the way you'd describe the audience or scenario to a colleague; the
model backends translate it into a prompt or typed question per item.
