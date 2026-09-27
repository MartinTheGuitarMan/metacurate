"""A JevClient backed by Laya (https://github.com/receptron/laya): an
open-source, Jev-compatible System One decision model that runs locally via
ONNX Runtime, from Convai Innovations.

Laya ships as a Node.js package, not a Python one, so `LayaClient` shells out
to a small bundled bridge script (`jev_laya_bridge.mjs`) rather than binding
to it directly. This is a stand-in for the real, waitlisted Jev API: swap
`LayaClient` for the real client once you have access, with no other changes
to `metacurate`.

Requires Node.js 20+ and `npm install @receptron/laya` on the machine running
metacurate. Laya's ~1.7GB ONNX weights auto-download from Hugging Face on
first use.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import NoulAnswer, NoulQuestion

_BRIDGE_SCRIPT = Path(__file__).parent / "jev_laya_bridge.mjs"


class LayaClient:
    """Implements JevClient.ask_noul by running Laya through a Node.js bridge."""

    def __init__(self, node_bin: str = "node", script: Path | None = None, timeout: float = 300.0):
        self._node_bin = node_bin
        self._script = script or _BRIDGE_SCRIPT
        self._timeout = timeout

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        try:
            parsed_state = json.loads(state)
        except json.JSONDecodeError:
            parsed_state = state

        payload = {
            "state": parsed_state,
            "questions": [{"id": q.id, "statement": q.statement} for q in questions],
        }

        try:
            result = subprocess.run(
                [self._node_bin, str(self._script)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"'{self._node_bin}' not found; Laya requires Node.js 20+ "
                "and `npm install @receptron/laya` "
                "(https://github.com/receptron/laya)"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Laya bridge failed: {exc.stderr}") from exc

        response = json.loads(result.stdout)
        return [
            NoulAnswer(id=answer["id"], probability=answer["probability"])
            for answer in response["answers"]
        ]
