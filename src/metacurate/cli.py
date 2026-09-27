from __future__ import annotations

import argparse

from .catalog import Catalog
from .curator import Curator
from .models import AnthropicModel


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="metacurate",
        description="Curate a metadata catalog into a list for a specific use case.",
    )
    parser.add_argument("catalog", help="Path to a catalog file (.json or .csv)")
    parser.add_argument("use_case", help="Description of the use case to curate for")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Max items to return")
    parser.add_argument("-m", "--model", default="claude-sonnet-5", help="Model to curate with")
    args = parser.parse_args()

    catalog = Catalog.from_csv(args.catalog) if args.catalog.endswith(".csv") else Catalog.from_json(args.catalog)

    curator = Curator(model=AnthropicModel(model=args.model))
    results = curator.curate(catalog, args.use_case, limit=args.limit)

    for rank, result in enumerate(results, start=1):
        print(f"{rank}. {result.item.id} — {result.rationale}")


if __name__ == "__main__":
    main()
