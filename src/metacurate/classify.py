"""Classify a single raw item against a fixed set of labeled candidates,
using a System One model's Noul primitive — one typed question per
candidate label, evaluated against the raw item as shared state in a
single pass.

This is the mirror image of `SystemOneModel`: SystemOneModel ranks many
catalog items against one use case description; `classify` ranks many
candidate labels against one piece of state (e.g. "which protocol is this
raw sample?").
"""

from __future__ import annotations

from .catalog import CatalogItem
from .models import NoulQuestion, SystemOneClient


def classify(
    client: SystemOneClient, state: str, labels: list[CatalogItem]
) -> list[tuple[str, float]]:
    """Score `state` against each label's description, most likely first.

    Each `CatalogItem` in `labels` is a candidate classification: its `id`
    is the label name, and its `metadata["description"]` is what the label
    means. Returns (label_id, probability) pairs sorted by probability
    descending.
    """
    questions = [
        NoulQuestion(
            id=label.id,
            statement=f"This sample matches: {label.metadata['description']}",
        )
        for label in labels
    ]
    answers = client.ask_noul(state, questions)
    ranked = sorted(answers, key=lambda answer: answer.probability, reverse=True)
    return [(answer.id, answer.probability) for answer in ranked]
