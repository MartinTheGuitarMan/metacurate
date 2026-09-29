from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .catalog import CatalogItem


class CurationModel(Protocol):
    """Anything that can pick and justify a subset of catalog items for a use case.

    Swap in whichever model you like (a System One model, an LLM, a rules
    engine, a human review queue) — the rest of metacurate only depends on
    this interface.
    """

    def curate(
        self, items: list[CatalogItem], use_case: str, limit: int
    ) -> list[tuple[str, str]]:
        """Return up to `limit` (item_id, rationale) pairs, most relevant first."""
        ...


@dataclass(frozen=True)
class NoulQuestion:
    """A single yes/no statement to evaluate against a System One model's shared state."""

    id: str
    statement: str


@dataclass(frozen=True)
class NoulAnswer:
    """A System One model's answer to one NoulQuestion: probability the statement is true, 0-1."""

    id: str
    probability: float


class SystemOneClient(Protocol):
    """The slice of a System One model's API/SDK metacurate needs.

    "System One" names a class of models — TypeSafe's Jev
    (https://en.wikipedia.org/wiki/Jev_(AI_model)) and open alternatives like
    Laya (see `metacurate.laya.LayaClient`) among them — that take a block of
    state (string, JSON object, or array of text) plus one or more typed
    questions, evaluated against that state in a single parallel pass, and
    return structured answers instead of free text. metacurate only uses the
    `Noul` primitive shared across these models — a yes/no statement scored
    0-1 — since it maps directly onto "how relevant is this item?" per
    catalog item.

    Bring your own System One model by implementing this seam: wrap
    whichever backend you have access to (Jev, Laya, or another) in a class
    with `ask_noul`, and hand it to `SystemOneModel`.
    """

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        ...


class SystemOneModel:
    """Curates using any System One model: one Noul question per catalog item
    ("is this item a strong match for the use case?"), evaluated against the
    whole catalog as shared state in a single request, then ranked by
    returned probability. Works with whatever `SystemOneClient` you bring.
    """

    def __init__(self, client: SystemOneClient):
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


@dataclass(frozen=True)
class ChoiceQuestion:
    """A single "pick one of these options" question to evaluate against a
    System One model's shared state."""

    id: str
    statement: str
    options: list[str]


@dataclass(frozen=True)
class ChoiceAnswer:
    """A System One model's answer to one ChoiceQuestion: the chosen option,
    plus the model's confidence in that choice, 0-1."""

    id: str
    choice: str
    confidence: float


class ChoiceClient(Protocol):
    """The slice of a System One model's API/SDK a `classify()`-style task
    needs — the `Choice` primitive, a sibling to `Noul` (see
    `SystemOneClient`) that picks one of several named options instead of a
    yes/no probability. Separate from `SystemOneClient` since not every
    backend that answers Noul questions also supports Choice (e.g. Laya, as
    currently wired up, only speaks Noul) — implement this only for a
    backend that actually can.
    """

    def ask_choice(self, state: str, questions: list[ChoiceQuestion]) -> list[ChoiceAnswer]:
        ...


class ClassificationModel(Protocol):
    """Anything that can assign every catalog item to one of a fixed set of
    categories. A different job than `CurationModel`: classify labels
    *every* item, it doesn't filter or rank a shortlist.
    """

    def classify(
        self, items: list[CatalogItem], question: str, categories: list[str]
    ) -> list[tuple[str, str, float]]:
        """Return (item_id, category, confidence) for every item, one pick each."""
        ...


class SystemOneClassifier:
    """Classifies using any System One model that supports Choice: one
    Choice question per catalog item, evaluated against the whole catalog as
    shared state in a single request, each item picking one of `categories`.
    """

    def __init__(self, client: ChoiceClient):
        self._client = client

    def classify(
        self, items: list[CatalogItem], question: str, categories: list[str]
    ) -> list[tuple[str, str, float]]:
        state = json.dumps([{"id": item.id, **item.metadata} for item in items])
        questions = [
            ChoiceQuestion(id=item.id, statement=f"For item '{item.id}': {question}", options=categories)
            for item in items
        ]
        answers = self._client.ask_choice(state, questions)
        return [(answer.id, answer.choice, answer.confidence) for answer in answers]
