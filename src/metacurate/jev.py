"""A SystemOneClient backed by TypeSafe's Jev (https://typesafe.ai), via the
official `typesafe-sdk` package (https://github.com/typesafe-ai/typesafe-sdk-python).

Install with `pip install metacurate[jev]` (or `pip install typesafe-sdk`
directly) and set `TYPESAFE_API_KEY` in the environment — `JevClient` defers
all configuration (API key, base URL, default model, timeout) to the
underlying SDK, which reads those from the environment the same way the
official client does, so no other setup is required.
"""

from __future__ import annotations

import json
from typing import Any

from .models import NoulAnswer, NoulQuestion


class JevClient:
    """Implements SystemOneClient.ask_noul against TypeSafe's Jev API.

    Sends every catalog item as one `system_one` call, one Noul question per
    item, keyed by item id. If the catalog is too large for a single request
    (`max_tokens_exceeded`), it's split in half and each half retried —
    recursively, so it converges on however many requests actually fit —
    rather than failing outright. When `state` is a JSON array of
    `{"id": ..., ...}` objects (what `SystemOneModel` builds), each half's
    state is narrowed to just its own items, so splitting actually reduces
    the tokens sent, not just the question count.
    """

    def __init__(self, **client_kwargs: Any):
        try:
            from typesafe_sdk import Noul, TypeSafeBadRequestError, TypeSafeClient
        except ImportError as exc:
            raise RuntimeError(
                "JevClient requires the `typesafe-sdk` package: "
                "`pip install typesafe-sdk` (or `pip install metacurate[jev]`), "
                "plus a TYPESAFE_API_KEY in the environment "
                "(see https://docs.typesafe.ai/sdk/python/)."
            ) from exc
        self._Noul = Noul
        self._TypeSafeBadRequestError = TypeSafeBadRequestError
        self._client = TypeSafeClient(**client_kwargs)

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        try:
            parsed_state = json.loads(state)
        except json.JSONDecodeError:
            parsed_state = state
        return self._ask_noul_batch(parsed_state, questions)

    def _ask_noul_batch(self, parsed_state, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        try:
            result = self._client.system_one(
                state=self._state_for(parsed_state, questions),
                questions={q.id: self._Noul(instructions=q.statement) for q in questions},
            )
        except self._TypeSafeBadRequestError as exc:
            if "max_tokens_exceeded" not in str(exc):
                raise
            if len(questions) <= 1:
                raise ValueError(
                    f"Item '{questions[0].id}' alone is too large for Jev to score "
                    "— its metadata plus the use case description exceed the "
                    "per-request token limit. Trim its metadata or shorten the "
                    "use case description."
                ) from exc
            mid = len(questions) // 2
            return self._ask_noul_batch(parsed_state, questions[:mid]) + self._ask_noul_batch(
                parsed_state, questions[mid:]
            )
        return [NoulAnswer(id=q.id, probability=result.nouls[q.id].noul) for q in questions]

    @staticmethod
    def _state_for(parsed_state, questions: list[NoulQuestion]):
        """Narrow `parsed_state` to just the items `questions` asks about, when
        it's a list of `{"id": ..., ...}` objects (SystemOneModel's shape).
        Anything else (a plain string, a dict, ...) can't be subset per-item,
        so it's sent unchanged — splitting still reduces the question count,
        just not the state.
        """
        if not isinstance(parsed_state, list):
            return parsed_state
        wanted = {q.id for q in questions}
        subset = [entry for entry in parsed_state if isinstance(entry, dict) and entry.get("id") in wanted]
        return subset if len(subset) == len(wanted) else parsed_state

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JevClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
