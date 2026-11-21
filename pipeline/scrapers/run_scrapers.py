
import time
import requests

from pipeline.utils import logger

from pipeline.scrapers.greenhouse import (
    fetch_greenhouse_jobs,
    save_raw_jobs as save_greenhouse_jobs,
)

from pipeline.scrapers.lever import (
    fetch_lever_jobs,
    save_raw_jobs as save_lever_jobs,
)

from pipeline.scrapers.hackernews import (
    fetch_hiring_thread,
    fetch_hiring_comments,
    filter_direct_comments,
    save_raw_comments,
)


def run_scrapers():
    logger.info("Starting job scraping...")

    greenhouse_companies = [
        "stripe",
        "airbnb",
        "databricks",
        "figma",
    ]

    lever_companies = [
        "palantir",
        "plaid",
    ]

    # Fetch Greenhouse jobs.
    for company in greenhouse_companies:
        try:
            jobs = fetch_greenhouse_jobs(company)
            save_greenhouse_jobs(company, jobs)
        except Exception as error:
            logger.error("Greenhouse failed for %s: %s", company, error)

        time.sleep(1)

    # Fetch Lever jobs.
    for company in lever_companies:
        try:
            jobs = fetch_lever_jobs(company)
            save_lever_jobs(company, jobs)
        except Exception as error:
            logger.error("Lever failed for %s: %s", company, error)

        time.sleep(1)

    # Fetch Hacker News hiring thread and comments.
    try:
        thread = fetch_hiring_thread()

        if thread:
            comments = fetch_hiring_comments(thread["objectID"])
            direct_comments = filter_direct_comments(
                comments,
                thread_id=thread["objectID"]
            )
            save_raw_comments(thread, comments)

            logger.info(
                "Saved %s direct Hacker News hiring comments",
                len(direct_comments),
            )
        else:
            logger.warning("No current-month Hacker News hiring thread found.")

    except Exception as error:
        logger.error("Hacker News scraping failed: %s", error)

    logger.info("Scraping stage completed.")
