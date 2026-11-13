import csv
import importlib.util
from pathlib import Path
import sys

import duckdb
import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
SPEC = importlib.util.spec_from_file_location("clean_table", PROJECT / "clean_table.py")
cleaner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleaner)


def write_records(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["record_id", "entity_name", "entity_id", "event_time", "amount", "country"])
        writer.writerows(rows)


def test_cleaning_reconciles_rows_and_preserves_missing_values(tmp_path):
    source = tmp_path / "source.csv"
    write_records(source, [
        ["1", "  Café   Market LLC ", "a", "09/19/2026", "$1,234.50", " us "],
        ["1", "Café Market LLC", "a", "2026-09-19", "1234.50", "US"],
        ["2", "Second Company", "b", "invalid", "10", "US"],
        ["3", "", "c", "2026-09-19", "1", "US"],
        ["4", "Missing Amount", "d", "", "", "PH"],
        ["5", "Invalid Price", "e", "2026-09-19", "bad", "PH"],
        ["6", "Invalid Country", "f", "2026-09-19", "1", "Philippines"],
        ["7", "Conflicting Company", "g", "2026-09-19", "1", "US"],
        ["7", "Different Company", "g", "2026-09-19", "1", "US"],
    ])
    report = cleaner.clean_table(source, tmp_path / "output")
    assert report["summary"]["input_records"] == 9
    assert report["summary"]["accepted_records"] == 2
    assert report["summary"]["rejected_records"] == 7
    assert report["summary"]["decisions"]["duplicate_record"] == 1
    assert report["summary"]["decisions"]["conflicting_record_id"] == 2
    with duckdb.connect() as connection:
        records = connection.read_parquet(str(tmp_path / "output/cleaned.parquet")).order("record_id").fetchall()
    assert records[0][2] == "Café Market LLC"
    assert records[0][3] == "cafe market llc"
    assert float(records[0][6]) == 1234.50
    assert report["summary"]["missing_values_retained"] == {"event_time": 1, "amount": 1, "country": 0}


def test_known_entity_ids_resolve_aliases_without_fuzzy_merges(tmp_path):
    source = tmp_path / "source.csv"
    write_records(source, [
        ["1", "Northwind Ltd", "same", "2026-01-01", "1", "US"],
        ["2", "Northwind Limited", "same", "2026-01-01", "1", "US"],
        ["3", "Northwind LLC", "other", "2026-01-01", "1", "US"],
    ])
    report = cleaner.clean_table(source, tmp_path / "output")
    assert report["summary"]["resolved_entities"] == 2
    candidates = list(csv.DictReader((tmp_path / "output/match_candidates.csv").open(encoding="utf-8")))
    assert len(candidates) == 1
    assert candidates[0]["decision"] == "review"


def test_candidate_blocking_separates_numeric_ids_and_countries():
    entities = [
        {"entity_key": "a", "canonical_name": "Acme 001 Ltd", "name_key": "acme 001 ltd", "country": "US"},
        {"entity_key": "b", "canonical_name": "Acme 001 LLC", "name_key": "acme 001 llc", "country": "US"},
        {"entity_key": "c", "canonical_name": "Acme 002 Ltd", "name_key": "acme 002 ltd", "country": "US"},
        {"entity_key": "d", "canonical_name": "Acme 001 Ltd", "name_key": "acme 001 ltd", "country": "PH"},
    ]
    candidates, counts = cleaner.candidate_matches(entities)
    assert [(entry["left_entity"], entry["right_entity"]) for entry in candidates] == [("a", "b")]
    assert counts["comparisons"] == 1


def test_overflow_blocks_are_reported():
    entities = [{"entity_key": str(index), "canonical_name": "Acme", "name_key": "acme", "country": "US"} for index in range(3)]
    candidates, counts = cleaner.candidate_matches(entities, max_block_size=2)
    assert candidates == []
    assert counts["entities_in_overflow_blocks"] == 3


def test_existing_output_and_missing_schema_fail_clearly(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("wrong,column\na,b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required columns"):
        cleaner.clean_table(source, tmp_path / "output")
    with pytest.raises(ValueError, match="already exists"):
        cleaner.clean_table(source, tmp_path / "output")


def test_record_output_is_reproducible(tmp_path):
    source = tmp_path / "source.csv"
    write_records(source, [["1", "Example Company", "", "2026-01-01", "1.25", "US"]])
    cleaner.clean_table(source, tmp_path / "first")
    cleaner.clean_table(source, tmp_path / "second")
    for filename in ("cleaned.csv", "entities.csv", "match_candidates.csv", "rejections.csv"):
        assert (tmp_path / "first" / filename).read_bytes() == (tmp_path / "second" / filename).read_bytes()
