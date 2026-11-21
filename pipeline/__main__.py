
import json

from pipeline.utils import logger
from pipeline.scrapers.run_scrapers import run_scrapers
from pipeline.processor import run_normalization
from pipeline.filters import run_filtering, generate_candidates
from pipeline.extractor import run_extraction, OUTPUT_FILE
from pipeline.database import create_tables, upsert_jobs, upsert_extractions
from pipeline.exporter import export_jobs_to_csv


def main():
    logger.info("Starting Job Intelligence Pipeline")

    # 1. Scrape job postings
    run_scrapers()

    # 2. Normalize and deduplicate jobs
    normalized_jobs = run_normalization()

    # 3. Filter jobs
    run_filtering()

    # 4. Generate candidates for LLM extraction
    candidates = generate_candidates()
    logger.info("Candidates available for extraction: %s", len(candidates))

    # 5. Extract structured information using Gemini
    run_extraction(limit=10)

    # 6. Store jobs and extracted data in SQLite
    create_tables()
    upsert_jobs(normalized_jobs)

    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            extracted_records = json.load(file)
        upsert_extractions(extracted_records)

    # 7. Export extracted records to CSV
    export_jobs_to_csv()

    logger.info("Job Intelligence Pipeline completed successfully.")


if __name__ == "__main__":
    main()
