from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CatalogItem:
    """One entry in a metadata catalog."""

    id: str
    metadata: dict[str, str] = field(default_factory=dict)


class Catalog:
    """A collection of metadata entries to curate from."""

    def __init__(self, items: list[CatalogItem]):
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    @classmethod
    def from_json(cls, path: str | Path) -> Catalog:
        data = json.loads(Path(path).read_text())
        items = [CatalogItem(id=str(entry.pop("id")), metadata=entry) for entry in data]
        return cls(items)

    @classmethod
    def from_csv(cls, path: str | Path) -> Catalog:
        with Path(path).open(newline="") as f:
            items = [CatalogItem(id=row.pop("id"), metadata=row) for row in csv.DictReader(f)]
        return cls(items)
