import csv
import json
import random

from pipeline.config import PROCESSED_DATA_DIR, LABELED_DATA_DIR
from pipeline.utils import logger


INPUT_FILE = PROCESSED_DATA_DIR / "extracted_jobs.json"
OUTPUT_FILE = LABELED_DATA_DIR / "manual_labels.csv"

EVALUATION_FIELDS = [
    "is_relevant",
    "is_us_role",
    "company",
    "title",
    "location",
    "country",
    "work_mode",
    "employment_type",
    "salary_min",
    "salary_max",
    "salary_currency",
    "experience_years_min",
    "experience_years_max",
    "required_skills",
    "preferred_skills",
]


def create_evaluation_dataset():

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    hn_records = [
        record for record in records
        if record["original_job"].get("source") == "hackernews"
    ]

    greenhouse_records = [
        record for record in records
        if record["original_job"].get("source") == "greenhouse"
    ]

    # Select 12 HN and 8 Greenhouse records.
    random_generator = random.Random(42)
    random_generator.shuffle(hn_records)
    random_generator.shuffle(greenhouse_records)

    selected_records = hn_records[:12] + greenhouse_records[:8]

    rows = []

    for record in selected_records:

        original = record["original_job"]
        extracted = record["extracted_data"]

        row = {
            "source": original.get("source"),
            "source_id": original.get("source_id"),
            "original_company": original.get("company"),
            "original_title": original.get("title"),
            "original_location": original.get("location"),
            "posting_url": original.get("url"),
            "posting_description": original.get("description"),
            "llm_evidence": json.dumps(
                extracted.get("evidence", []),
                ensure_ascii=False
            ),
        }

        for field in EVALUATION_FIELDS:

            value = extracted.get(field)

            row[f"llm_{field}"] = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (list, dict))
                else value
            )

            # Leave manual labels blank for human verification.
            row[f"manual_{field}"] = ""

        rows.append(row)

    LABELED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys()
        )

        writer.writeheader()
        writer.writerows(rows)

    logger.info("Manual evaluation dataset created.")
    logger.info("Total selected: %s", len(rows))
    logger.info("Hacker News: %s", sum(r["source"] == "hackernews" for r in rows))
    logger.info("Greenhouse: %s", sum(r["source"] == "greenhouse" for r in rows))
    logger.info("Output: %s", OUTPUT_FILE)


if __name__ == "__main__":
    create_evaluation_dataset()