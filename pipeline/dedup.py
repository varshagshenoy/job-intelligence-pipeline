
import re
from pipeline.utils import logger


def normalize_text(value):
    """
    Normalize text so small formatting differences
    don't prevent two records from matching.
    """
    if not value:
        return ""

    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def get_dedup_key(job):
    """
    Create a matching key using company, title, and location.
    """
    company = normalize_text(job.get("company"))
    title = normalize_text(job.get("title"))
    location = normalize_text(job.get("location"))

    return company, title, location


def deduplicate_jobs(jobs):
    """
    Remove duplicate jobs while preserving their source URLs.
    """
    unique_jobs = {}

    for job in jobs:
        key = get_dedup_key(job)

        if key not in unique_jobs:
            job["source_urls"] = []

            if job.get("url"):
                job["source_urls"].append(job["url"])

            unique_jobs[key] = job

        else:
            existing_job = unique_jobs[key]

            # Preserve URLs from all sources.
            new_url = job.get("url")

            if new_url and new_url not in existing_job["source_urls"]:
                existing_job["source_urls"].append(new_url)

            # Preserve the source names as well.
            sources = existing_job.setdefault("sources", [existing_job.get("source")])

            if job.get("source") and job["source"] not in sources:
                sources.append(job["source"])

    duplicate_count = len(jobs) - len(unique_jobs)

    logger.info("Input jobs: %s", len(jobs))
    logger.info("Unique jobs: %s", len(unique_jobs))
    logger.info("Duplicates removed: %s", duplicate_count)

    return list(unique_jobs.values())
