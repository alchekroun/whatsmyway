from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ADDRESSES_PATH = DATA_DIR / "paris_addresses.json"
CACHE_PATH = DATA_DIR / "paris_routes_cache.json"


def main() -> None:
    addresses = json.loads(ADDRESSES_PATH.read_text())
    coords = ";".join(f"{item['lng']},{item['lat']}" for item in addresses)
    query = urlencode({"annotations": "duration"})
    url = f"https://router.project-osrm.org/table/v1/driving/{coords}?{query}"

    with urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    durations_sec = payload["durations"]
    durations_min = [
        [round((value or 0.0) / 60, 2) for value in row]
        for row in durations_sec
    ]

    snapshot = {
        "provider": "osrm",
        "profile": "driving",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": url,
        "durations_min": durations_min,
    }
    CACHE_PATH.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(f"Saved routing snapshot for {len(addresses)} Paris addresses to {CACHE_PATH}")


if __name__ == "__main__":
    main()
