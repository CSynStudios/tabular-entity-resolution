# Implementation guidance

DuckDB reads source fields as text before explicit normalization. Unicode display names are normalized separately from accent-insensitive comparison keys. Optional missing values stay null; malformed nonempty values receive rejection decisions. Exact normalized duplicate rows are rejected. Repeated row IDs with different normalized values are conflicts rather than arbitrary first/last wins.

Provided entity IDs are scoped by country. Identifier-based grouping and exact normalized-name grouping are deterministic. Fuzzy matching produces review candidates and never overwrites a provided identifier or confirms physical identity. Legal suffixes are removed only from candidate comparison strings. Numeric tokens and country separate blocks; prefix blocking can miss cross-prefix aliases. Oversized blocks are reported and need a narrower source batch or a revised blocking strategy.

The million-row benchmark uses 1,000 provided entities and produces no fuzzy candidate comparisons. It measures ingestion, normalization, quality classification, deterministic grouping and output creation. It does not establish performance for one million distinct entities. The separate alias evaluation and public-host run exercise fuzzy comparisons.

benchmark.py samples process RSS every 50 ms. It is an observed resident-memory measure, not an exact memory-allocation trace. DuckDB's 512 MB budget does not include every native/process allocation. Preserve raw inputs and review rejected rows before downstream use.

Code contains no comments; reasoning and operational guidance remain here. CSV/Parquet outputs and host names stay local in ignored folders.
