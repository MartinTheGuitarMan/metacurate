from __future__ import annotations

import json
from dataclasses import dataclass
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


@dataclass(frozen=True)
class NoulQuestion:
    """A single yes/no statement to evaluate against Jev's shared state."""

    id: str
    statement: str


@dataclass(frozen=True)
class NoulAnswer:
    """Jev's answer to one NoulQuestion: probability the statement is true, 0-1."""

    id: str
    probability: float


class JevClient(Protocol):
    """The slice of the Jev API/SDK metacurate needs.

    A Jev request is a block of state (string, JSON object, or array of text)
    plus one or more typed questions, evaluated against that state in a single
    parallel pass (https://en.wikipedia.org/wiki/Jev_(AI_model)). metacurate
    only uses the `Noul` primitive — a yes/no statement scored 0-1 — since it
    maps directly onto "how relevant is this item?" per catalog item.

    TypeSafe hasn't published Jev's request/response wire format, auth scheme,
    or SDK package name, so this is the integration seam to implement against
    the real client once you have access to it, not a working network call.
    """

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        ...


class JevModel:
    """Curates using Jev: one Noul question per catalog item ("is this item a
    strong match for the use case?"), evaluated against the whole catalog as
    shared state in a single Jev request, then ranked by returned probability.
    """

    def __init__(self, client: JevClient):
        self._client = client

    def curate(
        self, items: list[CatalogItem], use_case: str, limit: int
    ) -> list[tuple[str, str]]:
        state = json.dumps([{"id": item.id, **item.metadata} for item in items])
        questions = [
            NoulQuestion(
                id=item.id,
                statement=f"Item '{item.id}' is a strong match for the use case: {use_case}",
            )
            for item in items
        ]
        answers = self._client.ask_noul(state, questions)
        ranked = sorted(answers, key=lambda answer: answer.probability, reverse=True)
        return [
            (answer.id, f"match probability {answer.probability:.2f}")
            for answer in ranked[:limit]
        ]
