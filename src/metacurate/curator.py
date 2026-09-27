from __future__ import annotations

from dataclasses import dataclass

from .catalog import Catalog, CatalogItem
from .models import CurationModel


@dataclass
class CurationResult:
    item: CatalogItem
    rationale: str


class Curator:
    """Curates a catalog into a use-case-specific list using a pluggable model."""

    def __init__(self, model: CurationModel):
        self.model = model

    def curate(self, catalog: Catalog, use_case: str, limit: int = 10) -> list[CurationResult]:
        items_by_id = {item.id: item for item in catalog}
        picks = self.model.curate(list(catalog), use_case, limit)
        return [
            CurationResult(item=items_by_id[item_id], rationale=rationale)
            for item_id, rationale in picks
            if item_id in items_by_id
        ]
