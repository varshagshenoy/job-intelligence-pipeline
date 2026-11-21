
import json
import os
import time
import hashlib
from google.genai.errors import ServerError

from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from pipeline.models import JobExtraction
from pipeline.config import PROCESSED_DATA_DIR
from pipeline.utils import logger


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.1-flash-lite"

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

INPUT_FILE = PROCESSED_DATA_DIR / "candidate_jobs.json"
OUTPUT_FILE = PROCESSED_DATA_DIR / "extracted_jobs.json"


def extract_job_information(job):
    """Use Gemini to extract structured information from one job posting."""

    
    prompt = f"""
You are an expert job posting information extraction assistant.

Extract structured information only from the job posting provided below.

STRICT EXTRACTION RULES:

1. Never invent, assume, or guess information.
2. If a field is not explicitly supported by the posting, return null.
3. Determine is_relevant based on the job title and responsibilities.
4. Determine is_us_role as follows:
   - true if the job location is explicitly in the United States
     or the posting explicitly offers US-remote work.
   - false if the job is explicitly located outside the United States
     with no US work option.
   - null if the location or eligibility is unclear.
5. A US office listing alone does not prove visa sponsorship
   or unrestricted work authorization.
6. Do not assume a job is US-remote just because it says Remote.
7. Extract the location from the job's stated location information.
8. Work mode must be Remote, Hybrid, On-site, or null.
9. Separate required skills from preferred skills:
   - Required skills come from minimum qualifications or requirements.
   - Preferred skills come from preferred or bonus qualifications.
10. Extract experience requirements:
   - For "3-5 years", minimum = 3 and maximum = 5.
   - For "4+ years", minimum = 4 and maximum = null.
   - If experience is not mentioned, both must be null.
11. Extract salary only when explicitly stated.
12. Required skills must not include preferred-only skills.
13. Evidence must be a list of objects, each containing:
    - field_name: name of the extracted field.
    - snippet: short, exact text from the posting supporting that field.
14. Provide evidence for every populated field whenever the
    source text supports it. Do not invent evidence.
15. Keep description_summary concise and factual.
16. For location-based fields, use the actual job location as evidence.
    Do not use a company's general office list as evidence of a job's location.
17. Provide evidence for every populated field whenever the posting
    contains a supporting statement or value.
18. For required_skills and preferred_skills, include separate evidence
    snippets supporting the extracted skills.
19. Do not include a skill in the output unless it is supported by
    the corresponding required or preferred section of the posting.

JOB POSTING:
{json.dumps(job, ensure_ascii=False, default=str)}
"""


    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JobExtraction,
            temperature=0
        )
    )

    extraction = JobExtraction.model_validate_json(response.text)

    usage_metadata = response.usage_metadata

    usage = {
        "input_tokens": getattr(usage_metadata, "prompt_token_count", None),
        "output_tokens": getattr(usage_metadata, "candidates_token_count", None),
        "total_tokens": getattr(usage_metadata, "total_token_count", None)
    }

    return extraction, usage

def get_job_key(job):
    """Generate a stable identifier for a job posting."""

    source = job.get("source", "")
    source_id = job.get("source_id", "")

    if source_id:
        return f"{source}:{source_id}"

    unique_text = "|".join([
        job.get("company", ""),
        job.get("title", ""),
        job.get("location", ""),
        job.get("url", "")
    ])

    return hashlib.sha256(
        unique_text.encode("utf-8")
    ).hexdigest()

    
def run_extraction(limit=None):
    """Extract jobs, resume previous work, and save progress."""

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        jobs = json.load(file)

    # Load previously extracted records, if available.
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            extracted_records = json.load(file)
    else:
        extracted_records = []

    # Identify jobs that have already been processed.
    processed_keys = {
        get_job_key(record["original_job"])
        for record in extracted_records
    }

    # Select only jobs that have not already been extracted.
    pending_jobs = [
        job for job in jobs
        if get_job_key(job) not in processed_keys
    ]

    if limit is not None:
        pending_jobs = pending_jobs[:limit]

    logger.info("Total candidate jobs: %s", len(jobs))
    logger.info("Previously extracted jobs: %s", len(processed_keys))
    logger.info("Jobs remaining to extract: %s", len(pending_jobs))

    for index, job in enumerate(pending_jobs, start=1):

        logger.info(
            "Extracting job %s of %s: %s",
            index,
            len(pending_jobs),
            job.get("title", "Unknown title")
        )

        try:
            for attempt in range(3):
                try:
                    extraction, usage = extract_job_information(job)
                    break

                except ServerError as error:
                    if attempt == 2:
                        raise

                    logger.warning(
                        "Gemini server error. Retrying attempt %s of 3: %s",
                        attempt + 2,
                        error
                    )
                    time.sleep(5 * (attempt + 1))

            record = {
                "original_job": job,
                "extracted_data": extraction.model_dump(),
                "usage": usage
            }

            extracted_records.append(record)
            processed_keys.add(get_job_key(job))

            logger.info("Successfully extracted job: %s", job.get("title"))

        except Exception as error:
            logger.exception(
                "Extraction failed for job %s: %s",
                job.get("title", "Unknown title"),
                error
            )

        # Save progress after every attempted job.
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
            json.dump(
                extracted_records,
                file,
                indent=4,
                ensure_ascii=False
            )

        time.sleep(2)

    logger.info(
        "Extraction completed. Total successful records: %s",
        len(extracted_records)
    )

    return extracted_records


if __name__ == "__main__":
    run_extraction(limit=5)
