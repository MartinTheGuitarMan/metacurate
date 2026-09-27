from metacurate.catalog import Catalog, CatalogItem
from metacurate.curator import Curator


class FakeModel:
    def curate(self, items, use_case, limit):
        return [(item.id, f"matches '{use_case}'") for item in items[:limit]]


def test_curator_returns_results_in_model_order():
    catalog = Catalog(
        [
            CatalogItem(id="a", metadata={"name": "Alpha"}),
            CatalogItem(id="b", metadata={"name": "Beta"}),
        ]
    )
    curator = Curator(model=FakeModel())

    results = curator.curate(catalog, "demo", limit=1)

    assert len(results) == 1
    assert results[0].item.id == "a"
    assert results[0].rationale == "matches 'demo'"


def test_curator_skips_unknown_ids():
    catalog = Catalog([CatalogItem(id="a", metadata={"name": "Alpha"})])

    class GhostModel:
        def curate(self, items, use_case, limit):
            return [("ghost", "not in catalog")]

    curator = Curator(model=GhostModel())

    assert curator.curate(catalog, "demo") == []
