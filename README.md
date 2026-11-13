# Tabular Cleaning and Entity Resolution

**Independent Project Showcase · v1.0.0**

[![Tests](https://github.com/CSynStudios/tabular-entity-resolution/actions/workflows/tests.yml/badge.svg)](https://github.com/CSynStudios/tabular-entity-resolution/actions/workflows/tests.yml)

A local DuckDB/RapidFuzz pipeline for traceable CSV cleaning, exact-record handling, identifier-based entity resolution and fuzzy candidate review. It exports cleaned CSV/Parquet, rejected-row decisions and entity reports.

The measured run processed **1,000,000 synthetic records in 34.34 seconds**, with **559.9 MiB** sampled peak RSS on the test machine. A separate public run processed **8,695 Inside Airbnb records**. See [VERIFICATION.md](VERIFICATION.md) for workload details and limits.


## Setup

Use Python 3.12. From this repository's root:

```powershell
conda env create --prefix ./.conda --file environment.yml
conda activate ./.conda
python -m pip check
python -m pytest -q
```

An existing Python 3.12 environment can use `python -m pip install -r requirements.txt -r requirements-dev.txt` instead. In the Veyra workspace, activate the one shared environment at the workspace root; separate local environments are not required. Runtime and test dependencies are pinned separately.


## Run

```powershell
python create_example.py --output data/synthetic --rows 100000
python clean_table.py --input data/synthetic/records.csv --output outputs/run
python evaluate_matching.py --output outputs/matching-evaluation
```

For the attributed public sample, run `python fetch_sample.py --output data/public`, then clean its records.csv. For a measured large run, generate a chosen row count and use `python benchmark.py --input data/synthetic/records.csv --output outputs/benchmark`. Each run requires a new output folder.

## CSV contract

| Column | Rule |
| --- | --- |
| record_id | Required row identifier; conflicting repeated IDs are rejected |
| entity_name | Required display name; whitespace, Unicode and comparison keys are normalized |
| entity_id | Optional provided entity identifier, scoped by country |
| event_time | Optional ISO date/time or US month/day/year date; invalid nonempty values are rejected |
| amount | Optional decimal; USD dollar signs and grouping commas are removed; invalid nonempty values are rejected |
| country | Optional two-letter code format, normalized to uppercase |

Outputs select these six canonical fields and generated trace fields. Additional source columns remain in the preserved input. Missing optional values stay null rather than being invented. Dates with timezone offsets and currency conversion are outside this contract.

## Resolution and outputs

Provided IDs resolve records within a country. Without an ID, exact normalized names define entities. RapidFuzz proposes additional matches in blocks by country, name prefix and numeric tokens. Its default score threshold is 92. Candidate rows always have a review decision; fuzzy matches are not automatically merged.

Outputs include cleaned.csv, cleaned.parquet, rejections.csv, entities.csv, match_candidates.csv and report.json. Input counts reconcile with accepted and rejected counts. The report records missing values, comparisons and entities skipped because a block exceeded its limit.

The engine uses a 512 MB DuckDB memory budget and four threads. Native process RSS can exceed that budget. Candidate matching supports up to 100,000 distinct entities, default blocks of 200 and at most 100,000 review pairs. Oversized blocks are reported; approximate blocking can miss matches. Structurally invalid CSV fails clearly rather than silently skipping malformed lines.

## Evidence and sources

Read [CASE_STUDY.md](CASE_STUDY.md), [VERIFICATION.md](VERIFICATION.md) and [GUIDANCE.md](GUIDANCE.md). The synthetic alias evaluation is reproducible; it is not a general accuracy estimate. Public candidate pairs require human review.

The downloader adapts the [Inside Airbnb Chicago snapshot](https://insideairbnb.com/get-the-data/) dated 19 September 2026, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The event date is the snapshot date, not a booking timestamp. Source records, host names and generated outputs are not committed.
