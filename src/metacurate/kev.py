"""A SystemOneClient backed by Kev (https://github.com/jaredpalmer/kev,
weights at https://huggingface.co/jaredpalmer): a family of small, locally
served System One decision models — LoRA adapters plus a pointer head over
Qwen bases (0.5B/0.6B/0.8B/4B/8B/9B/27B) — that speak TypeSafe's public
`/v1/systemone` HTTP contract, the same one Jev implements.

The 0.5B-0.8B sizes are documented as running comfortably on constrained
hardware such as an Apple Silicon Mac with 16GB of unified memory; kev-0.6b
is the documented latency/accuracy sweet spot there. Bigger sizes (4B+)
trade that headroom for more general knowledge.

Unlike Laya, Kev isn't a library to embed — it's served as its own local
HTTP process. `KevClient` doesn't start that process for you: run it
yourself with

    uv run --extra serve python -m kev.serve --run jaredpalmer/kev-0.6b --port 8009

(swap the `--run` model id for whichever size you downloaded), and point
`KevClient` at wherever it's listening.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .models import NoulAnswer, NoulQuestion


class KevClient:
    """Implements SystemOneClient.ask_noul by POSTing to a local `kev.serve` process."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8009",
        model: str = "kev-latest",
        timeout: float = 30.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def ask_noul(self, state: str, questions: list[NoulQuestion]) -> list[NoulAnswer]:
        payload = {
            "state": state,
            "model": self._model,
            "questions": {
                q.id: {"type": "noul", "instructions": q.statement} for q in questions
            },
        }
        request = urllib.request.Request(
            f"{self._base_url}/v1/systemone",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Kev server at {self._base_url} returned {exc.code}: {exc.read().decode()}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach a Kev server at {self._base_url}: {exc.reason}. Start one "
                "with `uv run --extra serve python -m kev.serve --run <model> --port ...` "
                "(https://github.com/jaredpalmer/kev)."
            ) from exc

        return [
            NoulAnswer(id=question_id, probability=answer["noul"])
            for question_id, answer in body["answers"].items()
        ]
