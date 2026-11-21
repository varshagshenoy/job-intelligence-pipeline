from pipeline.utils import logger, polite_get

import requests
from typing import Any
import json
from pathlib import Path
from datetime import datetime
import time

# Base URL for Greenhouse's public job board API
GREENHOUSE_API_URL = "https://boards-api.greenhouse.io/v1/boards"


def fetch_greenhouse_jobs(board_token: str) -> list[dict[str, Any]]:
    """
    Fetch all available job postings from one Greenhouse company board.
    """

    url = f"{GREENHOUSE_API_URL}/{board_token}/jobs"

    params = {
        "content": "true"
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

            # Do not retry permanent client errors, except rate limits (429).
            if 400 <= status_code < 500 and status_code != 429:
                logger.error(
                    "Permanent HTTP error for %s: %s",
                    board_token,
                    error
                )
                raise

            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt
            logger.warning(
                "Temporary HTTP error for %s. Retrying in %s seconds...",
                board_token,
                wait_time
            )
            time.sleep(wait_time)

        except requests.RequestException as error:
            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt
            logger.warning(
                "Request failed for %s. Retrying in %s seconds...",
                board_token,
                wait_time
            )
            time.sleep(wait_time)

    # Convert the JSON response into a Python dictionary
    data = response.json()

    jobs = data.get("jobs")

    if not isinstance(jobs, list):
        raise ValueError(
            f"Unexpected response format from Greenhouse for {board_token}"
        )

    logger.info(
        f"Successfully fetched {len(jobs)} jobs from {board_token}"
    )
    
    return jobs


def save_raw_jobs(company: str, jobs: list[dict[str, Any]]) -> None:
    """
    Save raw job postings to a JSON file.
    """

    # Create the raw data directory if it doesn't exist
    raw_data_dir = Path("data/raw")
    raw_data_dir.mkdir(parents=True, exist_ok=True)

    # Create a filename with company name and current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company}_{timestamp}.json"

    file_path = raw_data_dir / filename

    # Save the jobs as formatted JSON
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=4, ensure_ascii=False)

    logger.info(f"Saved {len(jobs)} jobs to {file_path}")


if __name__ == "__main__":

    companies = [
        "stripe",
        "airbnb",
        "databricks",
        "figma"
    ]

    for company in companies:
        try:
            jobs = fetch_greenhouse_jobs(company)
            save_raw_jobs(company, jobs)

            print(f"\nCompany: {company.upper()}")
            print(f"Total jobs fetched: {len(jobs)}")

        except requests.RequestException as error:
            logger.error(f"Error fetching {company}: {error}")

        time.sleep(1)  

