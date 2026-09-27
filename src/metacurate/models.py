from __future__ import annotations

import json
from typing import Protocol

from .catalog import CatalogItem


class CurationModel(Protocol):
    """Anything that can pick and justify a subset of catalog items for a use case.

    Swap in whichever model you like (Claude, another LLM, a rules engine, a human
    review queue) — the rest of metacurate only depends on this interface.
    """

    def curate(
        self, items: list[CatalogItem], use_case: str, limit: int
    ) -> list[tuple[str, str]]:
        """Return up to `limit` (item_id, rationale) pairs, most relevant first."""
        ...


class AnthropicModel:
    """Curates using a Claude model via the Anthropic API."""

    def __init__(self, model: str = "claude-sonnet-5", client=None):
        self.model = model
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self._client = client

    def curate(
        self, items: list[CatalogItem], use_case: str, limit: int
    ) -> list[tuple[str, str]]:
        catalog_text = "\n".join(f"- id={item.id}: {item.metadata}" for item in items)
        prompt = (
            f"Catalog of {len(items)} items:\n{catalog_text}\n\n"
            f"Use case: {use_case}\n\n"
            f"Pick the {limit} most relevant items for this use case. "
            'Respond with only a JSON array of objects: [{"id": "...", "why": "..."}, ...], '
            "most relevant first, no other text."
        )
        response = self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        picks = json.loads(response.content[0].text)
        return [(pick["id"], pick["why"]) for pick in picks[:limit]]
