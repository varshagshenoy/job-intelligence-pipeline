
import json
import pandas as pd

from pipeline.config import PROCESSED_DATA_DIR, EXPORTS_DIR
from pipeline.utils import logger


def export_jobs_to_csv():
    input_file = PROCESSED_DATA_DIR / "extracted_jobs.json"
    output_file = EXPORTS_DIR / "extracted_jobs.csv"

    if not input_file.exists():
        logger.warning("No extracted jobs file found. CSV export skipped.")
        return

    with open(input_file, "r", encoding="utf-8") as file:
        jobs = json.load(file)

    if not jobs:
        logger.warning("No extracted jobs available for export.")
        return

    rows = []

    for record in jobs:
        original_job = record.get("original_job", {})
        extracted_data = record.get("extracted_data", {})

        # Keep original job fields separate from extracted fields.
        row = {
            f"job_{key}": value
            for key, value in original_job.items()
        }

        row.update(extracted_data)
        rows.append(row)

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)

    # Convert nested lists and dictionaries into JSON strings.
    for column in df.columns:
        df[column] = df[column].apply(
            lambda value: json.dumps(value, ensure_ascii=False)
            if isinstance(value, (list, dict))
            else value
        )

    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    logger.info("Exported %s jobs to %s", len(df), output_file)

    return output_file
