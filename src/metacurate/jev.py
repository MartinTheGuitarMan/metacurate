"""A SystemOneClient backed by TypeSafe's Jev (https://typesafe.ai), via the
official `typesafe-sdk` package.

Requires `pip install typesafe-sdk` and a Jev API key from
https://console.typesafe.ai, either exported as `TYPESAFE_API_KEY` or passed
to `JevClient(api_key=...)`.
"""

from __future__ import annotations

import json
import os

from .models import NoulAnswer, NoulQuestion


class JevClient:
    """Implements SystemOneClient.ask_noul by calling Jev's `/v1/systemone` API."""

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 60.0):
        self._api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        self._model = model
        self._timeout = timeout

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        try:
            from typesafe_sdk import Noul, TypeSafeClient
        except ImportError as exc:
            raise RuntimeError(
                "typesafe-sdk not installed; Jev requires `pip install typesafe-sdk` "
                "and an API key from https://console.typesafe.ai"
            ) from exc

        if not self._api_key:
            raise RuntimeError(
                "No Jev API key found; set TYPESAFE_API_KEY or pass JevClient(api_key=...) "
                "(get a key from https://console.typesafe.ai)"
            )

        try:
            parsed_state = json.loads(state)
        except json.JSONDecodeError:
            parsed_state = state

        question_map = {q.id: Noul(instructions=q.statement) for q in questions}

        try:
            with TypeSafeClient(api_key=self._api_key, model=self._model, timeout=self._timeout) as client:
                response = client.system_one(state=parsed_state, questions=question_map)
        except Exception as exc:
            raise RuntimeError(f"Jev API call failed: {exc}") from exc

        return [
            NoulAnswer(id=question_id, probability=result.noul)
            for question_id, result in response.nouls.items()
        ]
