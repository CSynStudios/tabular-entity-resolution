import argparse
from collections import defaultdict
import csv
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import time

import duckdb
from rapidfuzz import fuzz

REQUIRED_COLUMNS = {"record_id", "entity_name", "entity_id", "event_time", "amount", "country"}


def entity_identifier(resolution_key):
    return "ent-" + hashlib.sha256(resolution_key.encode("utf-8")).hexdigest()[:20]


def candidate_matches(entities, threshold=92, max_block_size=200):
    blocks = defaultdict(list)
    for entity in entities:
        comparison_name = re.sub(r"\b(?:limited|ltd|llc|inc|incorporated|corporation|corp)\b", " ", entity["name_key"])
        comparison_name = " ".join(comparison_name.split())
        digits = "-".join(re.findall(r"\d+", comparison_name))
        block_key = (entity["country"] or "", comparison_name[:3], digits)
        blocks[block_key].append({**entity, "comparison_name": comparison_name})
    matches = []
    comparisons = 0
    overflow_entities = 0
    for block in blocks.values():
        if len(block) > max_block_size:
            overflow_entities += len(block)
            continue
        for left, right in combinations(block, 2):
            comparisons += 1
            score = fuzz.WRatio(left["comparison_name"], right["comparison_name"])
            if score < threshold:
                continue
            matches.append(
                {
                    "left_entity": left["entity_key"],
                    "right_entity": right["entity_key"],
                    "left_name": left["canonical_name"],
                    "right_name": right["canonical_name"],
                    "score": round(score, 4),
                    "decision": "review",
                }
            )
            if len(matches) > 100_000:
                raise ValueError("Candidate limit exceeded; use narrower source batches or stronger blocking.")
    return matches, {"comparisons": comparisons, "entities_in_overflow_blocks": overflow_entities}


def clean_table(input_path, output_directory, threshold=92, max_block_size=200):
    started = time.perf_counter()
    input_path = Path(input_path).resolve()
    output_directory = Path(output_directory).resolve()
    if not input_path.is_file():
        raise ValueError("Input must be an existing CSV file.")
    if output_directory.exists():
        raise ValueError("Output directory already exists; choose a new run directory.")
    if input_path.is_relative_to(output_directory):
        raise ValueError("Output must not contain the input file.")
    if not 0 <= threshold <= 100 or not 2 <= max_block_size <= 1000:
        raise ValueError("Threshold must be 0-100 and block size must be 2-1000.")
    output_directory.mkdir(parents=True)
    configuration = {"memory_limit": "512MB", "threads": "4", "temp_directory": str(output_directory / ".spill")}
    with duckdb.connect(config=configuration) as connection:
        connection.read_csv(str(input_path), header=True, all_varchar=True, strict_mode=True).create_view("incoming")
        columns = {column[0] for column in connection.execute("DESCRIBE incoming").fetchall()}
        if not REQUIRED_COLUMNS.issubset(columns):
            raise ValueError("Missing required columns: " + ", ".join(sorted(REQUIRED_COLUMNS - columns)))
        connection.execute(
            r"""
            CREATE TABLE normalized AS
            SELECT row_number() OVER () AS source_row,
                nullif(trim(record_id), '') AS record_id,
                nullif(regexp_replace(trim(nfc_normalize(entity_name)), '\s+', ' ', 'g'), '') AS entity_name,
                nullif(trim(regexp_replace(lower(strip_accents(entity_name)), '[^\p{L}\p{N}]+', ' ', 'g')), '') AS name_key,
                nullif(trim(entity_id), '') AS entity_id,
                nullif(trim(event_time), '') AS original_time,
                coalesce(try_strptime(trim(event_time), ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y'])) AS event_time,
                nullif(trim(amount), '') AS original_amount,
                try_cast(regexp_replace(trim(amount), '[$,\s]', '', 'g') AS DECIMAL(18,2)) AS amount,
                nullif(upper(trim(country)), '') AS country
            FROM incoming
            """
        )
        connection.execute(
            """
            CREATE TABLE classified AS
            WITH conflicts AS (
                SELECT record_id FROM normalized GROUP BY record_id
                HAVING count(DISTINCT (name_key, entity_id, event_time, amount, country)) > 1
            ), ranked AS (
                SELECT *, row_number() OVER (
                    PARTITION BY record_id, name_key, entity_id, event_time, amount, country ORDER BY source_row
                ) AS duplicate_rank FROM normalized
            )
            SELECT *, CASE
                WHEN record_id IS NULL THEN 'missing_record_id'
                WHEN name_key IS NULL THEN 'missing_entity_name'
                WHEN country IS NOT NULL AND NOT regexp_full_match(country, '[A-Z]{2}') THEN 'invalid_country'
                WHEN original_time IS NOT NULL AND event_time IS NULL THEN 'invalid_timestamp'
                WHEN original_amount IS NOT NULL AND amount IS NULL THEN 'invalid_amount'
                WHEN record_id IN (SELECT record_id FROM conflicts) THEN 'conflicting_record_id'
                WHEN duplicate_rank > 1 THEN 'duplicate_record'
                ELSE 'accepted' END AS decision
            FROM ranked
            """
        )
        summary_counts = dict(connection.execute("SELECT decision, count(*) FROM classified GROUP BY decision ORDER BY decision").fetchall())
        connection.execute(
            """
            CREATE TABLE cleaned AS
            SELECT source_row, record_id, entity_name, name_key, entity_id, event_time, amount, country,
                CASE WHEN entity_id IS NOT NULL THEN 'id:' || coalesce(country, '') || ':' || entity_id
                ELSE 'name:' || coalesce(country, '') || ':' || name_key END AS resolution_key
            FROM classified WHERE decision = 'accepted' ORDER BY source_row
            """
        )
        entity_count = connection.execute("SELECT count(DISTINCT resolution_key) FROM cleaned").fetchone()[0]
        if entity_count > 100_000:
            raise ValueError("More than 100,000 unique entities; split the source before candidate matching.")
        entity_rows = connection.execute(
            """
            SELECT resolution_key, min(entity_name), min(name_key), country, count(*)
            FROM cleaned GROUP BY resolution_key, country ORDER BY resolution_key
            """
        ).fetchall()
        entities = [
            {"entity_key": entity_identifier(key), "canonical_name": name, "name_key": name_key, "country": country, "record_count": count}
            for key, name, name_key, country, count in entity_rows
        ]
        candidates, matching_summary = candidate_matches(entities, threshold, max_block_size)
        connection.table("cleaned").write_parquet(str(output_directory / "cleaned.parquet"))
        connection.table("cleaned").write_csv(str(output_directory / "cleaned.csv"), header=True)
        connection.sql("SELECT source_row, record_id, decision FROM classified WHERE decision != 'accepted' ORDER BY source_row").write_csv(str(output_directory / "rejections.csv"), header=True)
        null_counts = connection.execute(
            "SELECT count(*) FILTER (WHERE event_time IS NULL), count(*) FILTER (WHERE amount IS NULL), count(*) FILTER (WHERE country IS NULL) FROM cleaned"
        ).fetchone()
    for filename, records, fieldnames in (
        ("entities.csv", entities, ["entity_key", "canonical_name", "name_key", "country", "record_count"]),
        ("match_candidates.csv", candidates, ["left_entity", "right_entity", "left_name", "right_name", "score", "decision"]),
    ):
        with (output_directory / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
    report = {
        "schema_version": 1,
        "summary": {
            "input_records": sum(summary_counts.values()),
            "accepted_records": summary_counts.get("accepted", 0),
            "rejected_records": sum(count for reason, count in summary_counts.items() if reason != "accepted"),
            "decisions": summary_counts,
            "resolved_entities": len(entities),
            "review_candidates": len(candidates),
            "missing_values_retained": dict(zip(["event_time", "amount", "country"], null_counts)),
            **matching_summary,
        },
        "settings": {"match_threshold": threshold, "max_block_size": max_block_size, "memory_limit": "512MB", "threads": 4},
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    (output_directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Clean canonical CSV records and produce reviewable entity matches.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=92)
    parser.add_argument("--max-block-size", type=int, default=200)
    arguments = parser.parse_args()
    try:
        report = clean_table(arguments.input, arguments.output, arguments.threshold, arguments.max_block_size)
    except (OSError, ValueError, duckdb.Error) as error:
        parser.exit(1, f"Cleaning failed: {error}\n")
    print(json.dumps(report["summary"], indent=2))
    if not report["summary"]["accepted_records"]:
        parser.exit(2, "No records were accepted; inspect report.json.\n")


if __name__ == "__main__":
    main()
