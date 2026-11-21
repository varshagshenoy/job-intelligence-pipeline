
import html
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Any


def clean_html(text: str) -> str:
    """Convert HTML content into readable plain text."""
    if not text:
        return ""

    text = html.unescape(text)
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def get_location(location: Any) -> str:
    """Handle different location formats."""
    if isinstance(location, dict):
        return location.get("name", "") or ""

    if isinstance(location, str):
        return location

    return ""


def normalize_greenhouse_job(
    job: dict[str, Any],
    company: str
) -> dict[str, Any]:

    return {
        "source": "greenhouse",
        "company": company,
        "source_id": str(job.get("id", "")),
        "title": job.get("title", ""),
        "location": get_location(job.get("location")),
        "description": clean_html(job.get("content", "")),
        "url": job.get("absolute_url", ""),
        "posted_at": job.get("first_published"),
        "raw_data": job
    }


def normalize_lever_job(
    job: dict[str, Any],
    company: str
) -> dict[str, Any]:

    categories = job.get("categories") or {}

    created_at = job.get("createdAt")
    posted_at = None

    if created_at:
        posted_at = datetime.fromtimestamp(
            created_at / 1000,
            tz=timezone.utc
        ).isoformat()

    return {
        "source": "lever",
        "company": company,
        "source_id": str(job.get("id", "")),
        "title": job.get("text", ""),
        "location": get_location(categories.get("location")),
        "description": clean_html(
            job.get("descriptionPlain")
            or job.get("description", "")
        ),
        "url": job.get("hostedUrl", ""),
        "posted_at": posted_at,
        "raw_data": job
    }


def normalize_hn_comment(
    comment: dict[str, Any]
) -> dict[str, Any]:

    text = clean_html(comment.get("comment_text", ""))

    # HN hiring posts commonly use:
    # Company | Job Title | Location | Other details
    first_line = text.split("\n")[0] if text else ""
    parts = [part.strip() for part in first_line.split("|")]

    company = parts[0] if len(parts) > 0 else ""
    title = parts[1] if len(parts) > 1 else ""
    location = parts[2] if len(parts) > 2 else ""

    created_at = comment.get("created_at")

    return {
        "source": "hackernews",
        "company": company,
        "source_id": str(comment.get("objectID", "")),
        "title": title,
        "location": location,
        "description": text,
        "url": (
            f"https://news.ycombinator.com/item?id="
            f"{comment.get('objectID', '')}"
        ),
        "posted_at": created_at,
        "raw_data": comment
    }
