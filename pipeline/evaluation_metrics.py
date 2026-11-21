
import json
import pandas as pd

from pipeline.config import LABELED_DATA_DIR

INPUT_FILE = LABELED_DATA_DIR / "manual_labels.csv"
FIELD_REPORT = LABELED_DATA_DIR / "evaluation_results.csv"
SUMMARY_REPORT = LABELED_DATA_DIR / "evaluation_summary.json"

FIELDS = [
    "is_relevant", "is_us_role", "company", "title", "location",
    "country", "work_mode", "employment_type", "salary_min",
    "salary_max", "salary_currency", "experience_years_min",
    "experience_years_max", "required_skills", "preferred_skills"
]

SKILL_FIELDS = {"required_skills", "preferred_skills"}
NUMERIC_FIELDS = {
    "salary_min", "salary_max",
    "experience_years_min", "experience_years_max"
}
BOOLEAN_FIELDS = {"is_relevant", "is_us_role"}


def normalize_scalar(value, field):
    value = str(value).strip()

    if value.lower() in ("", "null", "none", "nan"):
        return None

    if field in BOOLEAN_FIELDS:
        return value.lower() in ("true", "1", "yes")

    if field in NUMERIC_FIELDS:
        try:
            return float(value)
        except ValueError:
            return value.lower()

    return value.casefold()


def parse_skills(value):
    value = str(value).strip()

    if value.lower() in ("", "null", "none"):
        return set()

    try:
        items = json.loads(value)
        if isinstance(items, list):
            return {
                str(item).strip().casefold()
                for item in items if str(item).strip()
            }
    except (json.JSONDecodeError, TypeError):
        pass

    return {item.strip().casefold() for item in value.split(",") if item.strip()}


def calculate_metrics():
    df = pd.read_csv(INPUT_FILE, dtype=str, keep_default_na=False)

    field_results = []
    total_correct = 0
    total_comparisons = 0
    scalar_correct = 0
    scalar_comparisons = 0

    skill_counts = {
        field: {"tp": 0, "fp": 0, "fn": 0}
        for field in SKILL_FIELDS
    }

    for field in FIELDS:
        correct = 0

        for _, row in df.iterrows():
            predicted = row[f"llm_{field}"]
            actual = row[f"manual_{field}"]

            if field in SKILL_FIELDS:
                predicted_set = parse_skills(predicted)
                actual_set = parse_skills(actual)

                if predicted_set == actual_set:
                    correct += 1

                counts = skill_counts[field]
                counts["tp"] += len(predicted_set & actual_set)
                counts["fp"] += len(predicted_set - actual_set)
                counts["fn"] += len(actual_set - predicted_set)

            else:
                if normalize_scalar(predicted, field) == normalize_scalar(actual, field):
                    correct += 1

        total_correct += correct
        total_comparisons += len(df)

        if field not in SKILL_FIELDS:
            scalar_correct += correct
            scalar_comparisons += len(df)

        field_results.append({
            "field": field,
            "correct": correct,
            "total": len(df),
            "accuracy": round(correct / len(df), 4)
        })

    skill_results = {}

    for field, counts in skill_counts.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]

        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall else 0
        )

        skill_results[field] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4)
        }

    summary = {
        "postings_evaluated": len(df),
        "total_field_comparisons": total_comparisons,
        "overall_exact_match_accuracy": round(
            total_correct / total_comparisons, 4
        ),
        "non_skill_field_accuracy": round(
            scalar_correct / scalar_comparisons, 4
        ),
        "field_accuracy": field_results,
        "skill_metrics": skill_results,
        "skill_matching_method": "Normalized exact phrase matching"
    }

    pd.DataFrame(field_results).to_csv(FIELD_REPORT, index=False)

    with open(SUMMARY_REPORT, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    print(json.dumps(summary, indent=4))


if __name__ == "__main__":
    calculate_metrics()
