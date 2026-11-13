import argparse
import csv
import json
from pathlib import Path

from clean_table import clean_table, entity_identifier

NAMES = [
    ("north-1", "Northwind Logistics LLC"), ("north-2", "Northwind Logistics Ltd"),
    ("summit-1", "Summit Foods Inc"), ("summit-2", "Summit Food Incorporated"),
    ("cafe-1", "Cafe 42"), ("cafe-2", "Café 42"),
    ("harbor-1", "Harbour Workshop"), ("harbor-2", "Harbor Workshop"),
    ("north-other", "Northwind Packaging LLC"), ("summit-other", "Summit Software Inc"),
    ("cafe-other", "Cafe 43"), ("harbor-other", "Harbor Plumbing"),
]


def evaluate_matching(destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Evaluation destination already exists.")
    destination.mkdir(parents=True)
    with (destination / "records.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["record_id", "entity_name", "entity_id", "event_time", "amount", "country"])
        for identifier, name in NAMES:
            writer.writerow([identifier, name, identifier, "2026-01-01", "1.00", "US"])
    clean_table(destination / "records.csv", destination / "run")
    truth = {frozenset(entity_identifier(f"id:US:{prefix}-{suffix}") for suffix in [1, 2]) for prefix in ["north", "summit", "cafe", "harbor"]}
    with (destination / "run/match_candidates.csv").open(encoding="utf-8") as stream:
        predicted = {frozenset([record["left_entity"], record["right_entity"]]) for record in csv.DictReader(stream)}
    true_positives = len(truth & predicted)
    report = {"evaluation": "Constructed synthetic businesses; the four declared alias pairs are positive and all other pairs are negative", "records": len(NAMES), "positive_pairs": len(truth), "predicted_pairs": len(predicted), "true_positive_pairs": true_positives, "false_positive_pairs": len(predicted - truth), "false_negative_pairs": len(truth - predicted), "precision": true_positives / len(predicted) if predicted else 0, "recall": true_positives / len(truth)}
    (destination / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Evaluate entity-candidate decisions against explicit synthetic alias labels.")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        evaluate_matching(arguments.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")


if __name__ == "__main__":
    main()
