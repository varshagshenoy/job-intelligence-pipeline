# Job Intelligence Pipeline

A Python-based data engineering pipeline that collects job postings from multiple sources, filters relevant roles, deduplicates records, extracts structured information using an LLM, and stores the results in SQLite and CSV format.

## 1. Project Overview

The pipeline collects Data, Machine Learning, Analytics, and Platform Engineering job postings from:

- **Greenhouse:** Stripe, Airbnb, Databricks, Figma
- **Lever:** Palantir, Plaid
- **Hacker News:** Monthly "Who is hiring?" thread

It normalizes and filters job postings, uses Google's Gemini model to extract structured job information, and maintains a local database of collected jobs.

## 2. Architecture

The pipeline follows these stages:

1. **Scraping:** Fetch job postings using company job-board APIs and the Hacker News Algolia API.
2. **Normalization:** Convert source-specific records into a common structure and clean HTML descriptions.
3. **Deduplication:** Identify duplicate postings using normalized company, title, and location.
4. **Filtering:** Apply rule-based role-title and US-location filters.
5. **Candidate generation:** Prepare relevant role-title matches for LLM extraction.
6. **LLM extraction:** Use Gemini with a Pydantic response schema to extract structured job information and supporting evidence.
7. **Storage:** Store job records, extracted information, and change history in SQLite.
8. **Export:** Generate a CSV containing original job information and extracted fields.

## 3. Scraping Robustness

The scrapers use the following safeguards:

- Check each API host's `robots.txt` rules and cache them during execution.
- Maintain a minimum one-second delay between requests to the same host.
- Retry temporary network and server errors up to three times with exponential backoff.
- Avoid retrying permanent HTTP client errors, except HTTP 429 (rate limiting).
- Log source failures without stopping the remaining scraping process.
- Save timestamped raw API responses for traceability.

## 4. Extracted Information

The extraction schema includes:

- Company, job title, location, and country
- US-role relevance
- Work mode and employment type
- Salary range and currency
- Minimum and maximum experience requirements
- Required and preferred skills
- Job description summary
- Evidence snippets supporting extracted fields

The extraction prompt instructs the model not to guess missing information. Unstated fields are represented as null where applicable.

Pydantic validates the structured response.

## 5. Technology Stack

- Python 3.12
- Requests and BeautifulSoup
- Google Gemini API (`gemini-3.1-flash-lite`)
- Pydantic
- SQLite
- Pandas
- Pytest

## 6. Project Setup

### Prerequisites

- Python 3.12 or later
- Google Gemini API key

### Installation

Clone the repository and navigate to the project directory.

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

Do not commit the `.env` file or expose your API key.

## 7. Running the Pipeline

Run the complete pipeline using:

```bash
python -m pipeline
```

The pipeline performs scraping, normalization, filtering, candidate generation, LLM extraction, database updates, and CSV export.

LLM extraction is processed in batches of up to 10 pending jobs per pipeline run. Previously successful extractions are skipped on subsequent runs. Extraction results are saved incrementally to preserve progress.

## 8. Output Files

| File                                      | Description                          |
| ----------------------------------------- | ------------------------------------ |
| `data/raw/`                               | Timestamped raw source responses     |
| `data/processed/normalized_jobs.json`     | Normalized and deduplicated jobs     |
| `data/processed/filtered_jobs.json`       | Rule-based filtered job postings     |
| `data/processed/candidate_jobs.json`      | Jobs selected for LLM extraction     |
| `data/processed/extracted_jobs.json`      | Structured LLM extraction results    |
| `data/processed/token_usage_summary.json` | Aggregated token usage report        |
| `data/exports/extracted_jobs.csv`         | CSV export of extracted jobs         |
| `data/labeled/manual_labels.csv`          | Manually labelled evaluation dataset |
| `data/labeled/evaluation_results.csv`     | Field-level accuracy results         |
| `data/labeled/evaluation_summary.json`    | Evaluation summary                   |
| `data/jobs.db`                            | SQLite database                      |

## 9. Evaluation

A manually labelled dataset of 20 postings was created, containing:

- 12 Hacker News postings
- 8 Greenhouse postings

The evaluation compared LLM-extracted fields against manual labels across 15 fields.

| Metric                       | Result |
| ---------------------------- | -----: |
| Postings evaluated           |     20 |
| Field comparisons            |    300 |
| Overall exact-match accuracy | 86.67% |
| Non-skill field accuracy     | 95.00% |
| Required skills F1           | 60.91% |
| Preferred skills F1          | 67.89% |

Skill evaluation uses normalized exact phrase matching, so semantically similar but differently worded skills may be counted as mismatches.

Token usage reporting is implemented in `pipeline/token_usage.py`. However, token-level metadata was not retained for the initial 94 extractions, so historical token usage and measured cost per posting are unavailable. Future extractions capture input, output, and total token counts. Cost can be estimated using the applicable model pricing.

### Automated Tests

Run tests using:

```bash
pytest -v
```

The test suite currently contains 6 passing tests covering deduplication, source URL preservation, and database change history.

## 10. Design Decisions and Limitations

- **Deduplication:** Uses normalized company, title, and location. This is simple and effective for common duplicates, but title or location changes may create a separate canonical record.
- **Incremental extraction:** Previously extracted jobs are skipped, and extraction results are saved after each attempt.
- **Change history:** Changes to tracked job fields are recorded in a separate history table.
- **Source availability:** Plaid's configured Lever endpoint returned HTTP 404 during collection, so no Plaid postings were retrieved through that connector.
- **Job closure tracking:** Records are marked active when observed, but a complete missing-job reconciliation process is not yet implemented.
- **LLM cost tracking:** Token usage capture and reporting are implemented for new extractions. Historical usage is unavailable for the initial extraction batch, and actual cost per posting has not been measured.
- **Evaluation:** The manually labelled sample is relatively small and should not be treated as representative of every job source or role type.

## 11. Scaling to 5,000 Sources Weekly

For larger-scale operation, the pipeline could be extended by:

- Running source collectors as parallel, independently scheduled workers.
- Introducing a queue such as Celery with Redis or RabbitMQ.
- Using PostgreSQL for concurrent writes and centralized storage.
- Adding source-specific rate limits, retries, monitoring, and failure alerts.
- Tracking source freshness and reconciling inactive or closed postings.
- Using extraction caching, token-usage tracking, and controlled batch processing to manage LLM cost.
- Partitioning processing by source and scheduling weekly incremental updates.

These improvements would make the pipeline more resilient and suitable for larger production workloads.

---

**Project:** Job Intelligence Pipeline  
**Language:** Python  
**Storage:** SQLite and CSV  
**LLM:** Google Gemini
