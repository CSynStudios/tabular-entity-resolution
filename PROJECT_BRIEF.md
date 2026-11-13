# Project brief

## Intended problem

Inconsistent strings, timestamp formats and duplicate entity records make tabular sources difficult to analyze. This project should show traceable cleaning decisions and measurable entity-matching behavior.

## Implementation scope

Use one permitted public dataset and a bounded sample. Record source URL, access date, license, selected columns and sampling rules. Preserve raw inputs locally. Normalize only fields whose meaning has been established. Report missingness and rejected rows instead of silently inventing missing values.

Build candidate entity matches and evaluate them against labeled positive and negative examples. A fuzzy score alone must not be presented as proof that two records refer to the same entity.

## Completion criteria

1. A repeatable command produces cleaned records, a change report and an entity-match review file.
2. Record counts reconcile through every operation, including rejects and duplicate decisions.
3. Tests exercise inconsistent strings, malformed timestamps, missing fields and matching errors.
4. The evaluation reports the labeling method, thresholds, precision and recall, including limitations.
5. A larger-volume run records actual row count, time and memory before making scale claims.

## Deferred decisions

Polars or DuckDB is a candidate for the execution engine; choose one against the selected source. RapidFuzz is a candidate for match scoring. No processing packages are installed for this repository.

## Publication boundary

The repository currently contains the project specification and environment setup. Keep source records, generated results, private identifiers and credentials out of commits. A future case study must distinguish measured results from proposals.
