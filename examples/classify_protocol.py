"""Classify raw maritime telemetry samples by protocol/message type using a
System One model.

Each candidate protocol is a labeled `CatalogItem` (protocol_labels.json,
next to this file); each raw sample is scored against every candidate in
one `ask_noul` call via `metacurate.classify.classify`, ranked by returned
probability. The classifier itself (`classify`) has no protocol-specific
knowledge — only these labels and samples do.

Samples below are drawn verbatim from the sample_data/ fixtures in the
llm-maritime-protocol-translator-experiment repo (one NMEA GGA line, one
NMEA RMC line, one Modbus-style engine telemetry record).

Needs a Kev server running locally, e.g.:

    uv run --extra serve python -m kev.serve --run jaredpalmer/kev-0.6b --port 8009
    python examples/classify_protocol.py
"""

from __future__ import annotations

from pathlib import Path

from metacurate.catalog import Catalog
from metacurate.classify import classify
from metacurate.kev import KevClient

SAMPLES = {
    "gga_line": "$GPGGA,080000,5419.3980,N,01008.3640,E,1,07,1.3,2.7,M,46.9,M,,*42",
    "rmc_line": "$GPRMC,080000,A,5419.3980,N,01008.3640,E,8.3,92.2,210926,,,A*47",
    "engine_record": (
        '{"timestamp": "2026-09-21T08:00:00Z", "device_id": "engine-1", '
        '"registers": {"0": 1710, "1": 816, "2": 918, "3": 12345, "4": 0}}'
    ),
}


def main() -> None:
    labels_path = Path(__file__).parent / "protocol_labels.json"
    labels = list(Catalog.from_json(labels_path))
    client = KevClient()

    for name, sample in SAMPLES.items():
        ranked = classify(client, sample, labels)
        print(f"{name}:")
        for label_id, probability in ranked:
            print(f"  {label_id} (p={probability:.2f})")


if __name__ == "__main__":
    main()
