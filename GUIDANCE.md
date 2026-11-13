# Implementation guidance

This Independent Project Showcase currently contains the project specification and environment setup. Keep future code explanations in this Markdown file rather than adding comments to code.

Use the existing shared Conda environment while working inside the Veyra project workspace. The repository-specific environment file provides a minimal starting point for an independent clone; it does not install a second environment automatically.

Choose one execution engine after inspecting the actual dataset. Add only dependencies required by the next implementation stage, record their versions and update setup instructions. Start with explicit cleaning rules and a small evaluation before optimizing throughput.

Matching should produce reviewable candidates. Protect against false merges by retaining source identifiers locally, testing ambiguous pairs and recording confidence thresholds. Do not impute values without a defensible rule or call a fuzzy string match a confirmed identity.

Performance descriptions must identify the tested row count, machine and measurements. No benchmark or accuracy result exists yet.
