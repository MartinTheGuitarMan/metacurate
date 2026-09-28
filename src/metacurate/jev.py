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

    Batches every catalog item into a single `system_one` call, one Noul
    question per item, keyed by item id.
    """

    def __init__(self, **client_kwargs: Any):
        try:
            from typesafe_sdk import Noul, TypeSafeClient
        except ImportError as exc:
            raise RuntimeError(
                "JevClient requires the `typesafe-sdk` package: "
                "`pip install typesafe-sdk` (or `pip install metacurate[jev]`), "
                "plus a TYPESAFE_API_KEY in the environment "
                "(see https://docs.typesafe.ai/sdk/python/)."
            ) from exc
        self._Noul = Noul
        self._client = TypeSafeClient(**client_kwargs)

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        try:
            parsed_state = json.loads(state)
        except json.JSONDecodeError:
            parsed_state = state

        result = self._client.system_one(
            state=parsed_state,
            questions={q.id: self._Noul(instructions=q.statement) for q in questions},
        )
        return [NoulAnswer(id=q.id, probability=result.nouls[q.id].noul) for q in questions]

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JevClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
