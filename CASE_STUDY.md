# Traceable tabular cleaning and entity review

**Independent Project Showcase**

The system preserves source records while making normalization, rejection and identity decisions inspectable. DuckDB handles the larger record set; RapidFuzz proposes candidates within documented blocks without automatically merging uncertain identities.

A measured one-million-record synthetic run completed in 34.34 seconds with 559.9 MiB sampled peak RSS. It accepted 997,988 rows and explained 2,012 rejections. A separate 12-record labeled alias check recovered its four declared pairs with no extra pairs. The public run processed 8,695 records and retained missing prices as null.

The benchmark measures its stated workload rather than arbitrary entity-cardinality scale. Public fuzzy candidates remain review decisions. VERIFICATION.md records counts and limits; GUIDANCE.md explains the grouping and blocking choices.
