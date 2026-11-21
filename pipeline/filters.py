
import json
import re

from pipeline.config import PROCESSED_DATA_DIR
from pipeline.utils import logger


# Roles relevant to the assignment
ROLE_KEYWORDS = [
    "data engineer",
    "analytics engineer",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "data scientist",
    "data analyst",
    "business intelligence engineer",
    "bi engineer",
    "platform engineer",
    "data platform engineer",
    "machine learning scientist",
    "research engineer",
]

# US states and territories
US_STATES = [
    "alabama", "alaska", "arizona", "arkansas", "california",
    "colorado", "connecticut", "delaware", "florida", "georgia",
    "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
    "kentucky", "louisiana", "maine", "maryland", "massachusetts",
    "michigan", "minnesota", "mississippi", "missouri", "montana",
    "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota",
    "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas",
    "utah", "vermont", "virginia", "washington", "west virginia",
    "wisconsin", "wyoming", "district of columbia"
]

US_STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC"
]

# Common US cities that may appear without a state name
US_CITIES = [
    "new york city", "san francisco", "los angeles", "seattle",
    "chicago", "boston", "austin", "denver", "atlanta",
    "miami", "san diego", "dallas", "houston", "portland",
    "philadelphia", "washington dc", "washington, dc",
    "san jose", "palo alto", "mountain view", "menlo park",
    "sunnyvale", "bellevue", "redmond", "cambridge",
    "brooklyn", "manhattan"
]


def is_relevant_title(title: str) -> bool:
    """Check whether a job title matches target role categories."""

    title = (title or "").lower()

    return any(keyword in title for keyword in ROLE_KEYWORDS)



def is_us_location(location: str) -> bool:
    """Identify locations with explicit evidence of US eligibility."""

    location = (location or "").lower().strip()

    if not location:
        return False

    # Exact US labels and explicit US remote locations
    if location in {"us", "usa", "united states", "u.s."}:
        return True

    us_indicators = [
        "united states",
        "united states of america",
        "usa",
        "u.s.",
        "us only",
        "us-based",
        "us based",
        "us citizen",
        "us - remote",
        "us remote",
        "remote (us)",
        "remote - us",
    ]

    if any(term in location for term in us_indicators):
        return True

    for state in US_STATES:
        if re.search(r"\b" + re.escape(state) + r"\b", location):
            return True

    for code in US_STATE_CODES:
        if re.search(r",\s*" + code.lower() + r"\b", location):
            return True

    if any(city in location for city in US_CITIES):
        return True

    # Deliberately do not accept "Remote" alone.
    return False



def filter_jobs(jobs: list[dict]) -> list[dict]:
    """Keep relevant engineering/analytics roles in the US."""

    filtered = []

    for job in jobs:
        if not is_relevant_title(job.get("title", "")):
            continue

        if not is_us_location(job.get("location", "")):
            continue

        filtered.append(job)

    return filtered


def run_filtering():
    """Load normalized jobs, filter them, and save the results."""

    input_file = PROCESSED_DATA_DIR / "normalized_jobs.json"

    with open(input_file, "r", encoding="utf-8") as file:
        jobs = json.load(file)

    filtered_jobs = filter_jobs(jobs)

    output_file = PROCESSED_DATA_DIR / "filtered_jobs.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(filtered_jobs, file, indent=2, ensure_ascii=False)

    logger.info(f"Input records: {len(jobs)}")
    logger.info(f"Filtered records: {len(filtered_jobs)}")
    logger.info(f"Removed records: {len(jobs) - len(filtered_jobs)}")

    print("\nFiltering complete!")
    print(f"Input records: {len(jobs)}")
    print(f"Relevant US jobs: {len(filtered_jobs)}")
    print(f"Output: {output_file}")

    return filtered_jobs

def generate_candidates():
    input_file = PROCESSED_DATA_DIR / "normalized_jobs.json"
    output_file = PROCESSED_DATA_DIR / "candidate_jobs.json"

    with open(input_file, "r", encoding="utf-8") as file:
        jobs = json.load(file)

    candidates = [
        job for job in jobs
        if is_relevant_title(job.get("title", ""))
    ]

    candidates.sort(
        key=lambda job: (
            job.get("source") != "hackernews",
            job.get("company", "").lower()
        )
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(candidates, file, indent=4, ensure_ascii=False)

    hn_count = sum(
        job.get("source") == "hackernews"
        for job in candidates
    )

    logger.info("Candidate jobs generated: %s", len(candidates))
    logger.info("Hacker News candidates: %s", hn_count)

    return candidates

if __name__ == "__main__":
    run_filtering()
