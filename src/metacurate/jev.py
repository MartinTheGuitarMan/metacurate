"""A SystemOneClient (and ChoiceClient) backed by TypeSafe's Jev
(https://typesafe.ai), via the official `typesafe-sdk` package
(https://github.com/typesafe-ai/typesafe-sdk-python).

Install with `pip install metacurate[jev]` (or `pip install typesafe-sdk`
directly) and set `TYPESAFE_API_KEY` in the environment — `JevClient` defers
all configuration (API key, base URL, default model, timeout) to the
underlying SDK, which reads those from the environment the same way the
official client does, so no other setup is required.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .models import ChoiceAnswer, ChoiceQuestion, NoulAnswer, NoulQuestion


class JevClient:
    """Implements SystemOneClient.ask_noul and ChoiceClient.ask_choice against
    TypeSafe's Jev API.

    Sends every catalog item as one `system_one` call, one question per item,
    keyed by item id. If the catalog is too large for a single request
    (`max_tokens_exceeded`), it's split in half and each half retried —
    recursively, so it converges on however many requests actually fit —
    rather than failing outright. When `state` is a JSON array of
    `{"id": ..., ...}` objects (what `SystemOneModel`/`SystemOneClassifier`
    build), each half's state is narrowed to just its own items, so
    splitting actually reduces the tokens sent, not just the question count.
    """

    def __init__(self, **client_kwargs: Any):
        try:
            from typesafe_sdk import Choice, Noul, TypeSafeBadRequestError, TypeSafeClient
        except ImportError as exc:
            raise RuntimeError(
                "JevClient requires the `typesafe-sdk` package: "
                "`pip install typesafe-sdk` (or `pip install metacurate[jev]`), "
                "plus a TYPESAFE_API_KEY in the environment "
                "(see https://docs.typesafe.ai/sdk/python/)."
            ) from exc
        self._Noul = Noul
        self._Choice = Choice
        self._TypeSafeBadRequestError = TypeSafeBadRequestError
        self._client = TypeSafeClient(**client_kwargs)

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        by_id = {q.id: q for q in questions}
        return self._run_batch(
            self._parse_state(state),
            list(by_id),
            build_question=lambda item_id: self._Noul(instructions=by_id[item_id].statement),
            build_answer=lambda result, item_id: NoulAnswer(
                id=item_id, probability=result.nouls[item_id].noul
            ),
        )

    def ask_choice(self, state: str, questions: list[ChoiceQuestion]) -> list[ChoiceAnswer]:
        by_id = {q.id: q for q in questions}
        return self._run_batch(
            self._parse_state(state),
            list(by_id),
            build_question=lambda item_id: self._Choice(
                instructions=by_id[item_id].statement,
                criteria={option: None for option in by_id[item_id].options},
            ),
            build_answer=lambda result, item_id: ChoiceAnswer(
                id=item_id,
                choice=result.choices[item_id].choice,
                confidence=result.choices[item_id].confidence,
            ),
        )

    @staticmethod
    def _parse_state(state: str):
        try:
            return json.loads(state)
        except json.JSONDecodeError:
            return state

    def _run_batch(
        self,
        parsed_state,
        ids: list[str],
        build_question: Callable[[str], Any],
        build_answer: Callable[[Any, str], Any],
    ) -> list[Any]:
        """Shared chunking/retry core for ask_noul and ask_choice.

        `build_question(item_id)` builds the SDK question object to send for
        that item; `build_answer(result, item_id)` pulls that item's answer
        back out of a successful response. Both are primitive-specific
        (Noul vs. Choice); the batching, state-narrowing, and
        max_tokens_exceeded splitting logic around them isn't.
        """
        try:
            result = self._client.system_one(
                state=self._state_for(parsed_state, ids),
                questions={item_id: build_question(item_id) for item_id in ids},
            )
        except self._TypeSafeBadRequestError as exc:
            if "max_tokens_exceeded" not in str(exc):
                raise
            if len(ids) <= 1:
                raise ValueError(
                    f"Item '{ids[0]}' alone is too large for Jev to score — its "
                    "metadata plus the question/use case description exceed the "
                    "per-request token limit. Trim its metadata or shorten the "
                    "question."
                ) from exc
            mid = len(ids) // 2
            return self._run_batch(
                parsed_state, ids[:mid], build_question, build_answer
            ) + self._run_batch(parsed_state, ids[mid:], build_question, build_answer)
        return [build_answer(result, item_id) for item_id in ids]

    @staticmethod
    def _state_for(parsed_state, ids: list[str]):
        """Narrow `parsed_state` to just `ids`, when it's a list of
        `{"id": ..., ...}` objects (SystemOneModel/SystemOneClassifier's
        shape). Anything else (a plain string, a dict, ...) can't be subset
        per-item, so it's sent unchanged — splitting still reduces the
        question count, just not the state.
        """
        if not isinstance(parsed_state, list):
            return parsed_state
        wanted = set(ids)
        subset = [entry for entry in parsed_state if isinstance(entry, dict) and entry.get("id") in wanted]
        return subset if len(subset) == len(wanted) else parsed_state

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JevClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
