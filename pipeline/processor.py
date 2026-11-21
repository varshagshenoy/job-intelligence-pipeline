
import json
from datetime import datetime
from pathlib import Path

from pipeline.config import RAW_DATA_DIR, PROCESSED_DATA_DIR
from pipeline.normalizer import (
    normalize_greenhouse_job,
    normalize_lever_job,
    normalize_hn_comment
)
from pipeline.utils import logger
from pipeline.dedup import deduplicate_jobs


def latest_file(pattern: str) -> Path:
    """Find the most recently modified file matching a pattern."""
    files = list(RAW_DATA_DIR.glob(pattern))

    if not files:
        logger.warning(f"No raw files found for: {pattern}")
        return None

    return max(files, key=lambda file: file.stat().st_mtime)


def load_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def process_greenhouse(company: str) -> list[dict]:
    file_path = latest_file(f"{company}_*.json")

    if not file_path:
        return []

    raw_jobs = load_json(file_path)

    normalized = [
        normalize_greenhouse_job(job, company.title())
        for job in raw_jobs
    ]

    logger.info(
        f"Normalized {len(normalized)} Greenhouse jobs for {company}"
    )

    return normalized


def process_lever(company: str) -> list[dict]:
    file_path = latest_file(f"{company}_*.json")

    if not file_path:
        return []

    raw_jobs = load_json(file_path)

    normalized = [
        normalize_lever_job(job, company.title())
        for job in raw_jobs
    ]

    logger.info(
        f"Normalized {len(normalized)} Lever jobs for {company}"
    )

    return normalized


def process_hackernews() -> list[dict]:
    file_path = latest_file("hackernews_*.json")

    if not file_path:
        return []

    raw_data = load_json(file_path)

    thread_id = str(raw_data["thread"].get("objectID", ""))

    direct_comments = [
        comment
        for comment in raw_data["comments"]
        if str(comment.get("parent_id")) == thread_id
    ]

    normalized = [
        normalize_hn_comment(comment)
        for comment in direct_comments
    ]

    logger.info(
        f"Normalized {len(normalized)} Hacker News hiring comments"
    )

    return normalized


def run_normalization() -> list[dict]:
    """Normalize and combine records from all available sources."""

    all_jobs = []

    # Greenhouse companies
    for company in ["stripe", "airbnb", "databricks", "figma"]:
        all_jobs.extend(process_greenhouse(company))

    # Lever companies
    for company in ["palantir", "plaid"]:
        all_jobs.extend(process_lever(company))

    # Hacker News
    all_jobs.extend(process_hackernews())

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    output_file = PROCESSED_DATA_DIR / "normalized_jobs.json"

    # Log the total number of normalized records
    logger.info(f"Total normalized records: {len(all_jobs)}")

    # Remove duplicate jobs across sources
    unique_jobs = deduplicate_jobs(all_jobs)

    # Save only unique records
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(unique_jobs, file, indent=2, ensure_ascii=False)

    logger.info(f"Total unique records after deduplication: {len(unique_jobs)}")
    logger.info(f"Saved normalized data to {output_file}")

    return unique_jobs


if __name__ == "__main__":
    jobs = run_normalization()

    print("\nNormalization complete!")
    print(f"Total records: {len(jobs)}")
    print("Output: data/processed/normalized_jobs.json")
