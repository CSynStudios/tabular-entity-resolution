# Verification record

Release validation on 13 November 2026 used Windows, Python 3.12.16, DuckDB 1.5.6 and RapidFuzz 3.14.6. Six tests cover normalized values, missingness, row reconciliation, duplicate/conflicting IDs, deterministic resolution, candidate blocking/overflow, output preservation and reproducibility.

| Million-record synthetic run | Measured result |
| --- | --- |
| Input rows | 1,000,000 |
| Accepted rows | 997,988 |
| Rejected rows | 2,012 |
| Wall time including child startup | 34.340094 seconds |
| Sampled peak RSS | 559.898 MiB |
| Distinct provided-ID entities | 1,000 |
| Fuzzy comparisons in this workload | 0 |

The process used four DuckDB threads and a 512 MB engine memory budget. Resident process memory includes allocations beyond that budget. RSS was sampled every 50 ms. This is a single measured workload, not a universal throughput estimate.

The constructed alias evaluation contained 12 records and 4 positive pairs. It returned 4 true positives, 0 false positives and 0 false negatives (precision 1.00, recall 1.00 on these synthetic labels only).

The attributed Inside Airbnb run accepted 8,695 records, resolved 3,635 provided-ID entities and produced 7,835 review candidates from 30,907 comparisons in 0.632957 seconds. It preserved 1,243 missing prices. Public pairs are not labeled truth and were not auto-merged.

Reproduction: create_example.py, benchmark.py, evaluate_matching.py and fetch_sample.py generate or acquire the recorded inputs. Detailed results and source hashes stay in ignored local folders. The GitHub workflow runs the six offline tests from the pinned setup.
