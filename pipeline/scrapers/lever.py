import requests
from typing import Any
import json
import time
from pathlib import Path
from datetime import datetime

from pipeline.utils import logger, polite_get

LEVER_API_URL = "https://api.lever.co/v0/postings"


def fetch_lever_jobs(company: str) -> list[dict[str, Any]]:
    """
    Fetch all published job postings from a Lever company board.
    """

    url = f"{LEVER_API_URL}/{company}"

    params = {
        "mode": "json"
    }

    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = polite_get(
                url,
                params=params,
                timeout=30
            )

            response.raise_for_status()
            break

        
        except requests.HTTPError as error:
            status_code = error.response.status_code

            # Do not retry permanent client errors such as 404.
            if status_code < 500 and status_code != 429:
                logger.error(
                    "Permanent HTTP error for %s: %s",
                    company,
                    error
                )
                raise

            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt

            logger.warning(
                "Temporary HTTP error for %s. "
                "Retrying in %s seconds: %s",
                company,
                wait_time,
                error
            )
            time.sleep(wait_time)

        except requests.RequestException as error:
            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt

            logger.warning(
                "Request failed for %s. Retrying in %s seconds: %s",
                company,
                wait_time,
                error
            )
            time.sleep(wait_time)


    jobs = response.json()

    if not isinstance(jobs, list):
        raise ValueError(
            f"Unexpected response format from Lever for {company}"
        )

    logger.info(
        f"Successfully fetched {len(jobs)} jobs from {company}"
    )

    return jobs


def save_raw_jobs(company: str, jobs: list[dict[str, Any]]) -> None:
    """Save raw Lever job postings to a JSON file."""

    raw_data_dir = Path("data/raw")
    raw_data_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company}_{timestamp}.json"

    file_path = raw_data_dir / filename

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=4, ensure_ascii=False)

    logger.info(f"Saved {len(jobs)} jobs to {file_path}")


if __name__ == "__main__":

    companies = ["palantir", "plaid"]

    for company in companies:
        try:
            jobs = fetch_lever_jobs(company)
            save_raw_jobs(company, jobs)

            print(f"\nCompany: {company.upper()}")
            print(f"Total jobs fetched: {len(jobs)}")

            for job in jobs[:3]:
                print("Title:", job.get("text"))
                print("Location:", job.get("categories", {}).get("location"))
                print("URL:", job.get("hostedUrl"))
                print("-" * 50)

        except requests.RequestException as error:
            logger.error(f"Error fetching {company}: {error}")

        time.sleep(1)