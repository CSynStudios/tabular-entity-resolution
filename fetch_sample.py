import argparse
import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://data.insideairbnb.com/united-states/il/chicago/2026-09-19/visualisations/listings.csv"


def fetch_sample(destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Destination already exists.")
    with urlopen(Request(SOURCE_URL, headers={"User-Agent": "VeyraTabularCleaning/1.0"}), timeout=60) as response:
        payload = response.read(25_000_001)
    if len(payload) > 25_000_000:
        raise ValueError("Public sample exceeds the 25 MB download limit.")
    reader = csv.DictReader(StringIO(payload.decode("utf-8-sig")))
    if not {"id", "host_id", "host_name", "price"}.issubset(reader.fieldnames or []):
        raise ValueError("Public source columns changed; review the source before adapting it.")
    destination.mkdir(parents=True)
    (destination / "source.csv").write_bytes(payload)
    count = 0
    with (destination / "records.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["record_id", "entity_name", "entity_id", "event_time", "amount", "country"])
        for listing in reader:
            writer.writerow([listing["id"], listing["host_name"], listing["host_id"], "2026-09-19", listing["price"], "US"])
            count += 1
    manifest = {
        "url": SOURCE_URL,
        "source": "Inside Airbnb, Chicago, 19 September 2026",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "rows": count,
        "mapping": {"id": "record_id", "host_name": "entity_name", "host_id": "entity_id", "price": "amount"},
        "event_time": "Source snapshot date, not a booking or transaction timestamp",
    }
    (destination / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Saved and adapted {count} public listing records.")


def main():
    parser = argparse.ArgumentParser(description="Download a pinned Inside Airbnb snapshot and adapt its documented columns.")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        fetch_sample(arguments.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Download failed: {error}\n")


if __name__ == "__main__":
    main()
