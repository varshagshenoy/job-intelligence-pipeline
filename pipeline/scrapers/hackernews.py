import requests
from typing import Any
import json
import time
from pathlib import Path
from datetime import datetime

from pipeline.utils import logger, polite_get

HN_API_URL = "https://hn.algolia.com/api/v1"

def fetch_hn_json(url, params):
    """Fetch Hacker News API data with retries and backoff."""

    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = polite_get(
                url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as error:
            status_code = error.response.status_code

            if 400 <= status_code < 500 and status_code != 429:
                logger.error("Permanent Hacker News API error: %s", error)
                raise

            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt
            logger.warning(
                "Temporary Hacker News API error. "
                "Retrying in %s seconds: %s",
                wait_time,
                error
            )
            time.sleep(wait_time)

        except requests.RequestException as error:
            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt
            logger.warning(
                "Hacker News request failed. "
                "Retrying in %s seconds: %s",
                wait_time,
                error
            )
            time.sleep(wait_time)

def fetch_hiring_thread() -> dict[str, Any] | None:
    """
    Find the current month's Who is Hiring thread.
    """

    url = f"{HN_API_URL}/search_by_date"

    params = {
        "tags": "story,author_whoishiring",
        "hitsPerPage": 50
    }

    data = fetch_hn_json(url, params)
    hits = data.get("hits", [])

    current_month = datetime.now().strftime("%B %Y")

    for hit in hits:
        title = hit.get("title", "")

        if title == f"Ask HN: Who is hiring? ({current_month})":
            logger.info(f"Found hiring thread: {title}")
            return hit

    logger.warning(f"No hiring thread found for {current_month}")
    return None


def fetch_hiring_comments(thread_id: str) -> list[dict[str, Any]]:
    """
    Fetch all comments belonging to a hiring thread.
    """

    url = f"{HN_API_URL}/search"

    params = {
        "tags": f"comment,story_{thread_id}",
        "hitsPerPage": 1000
    }

    data = fetch_hn_json(url, params)
    comments = data.get("hits", [])

    logger.info(
        f"Fetched {len(comments)} comments from thread {thread_id}"
    )

    return comments


def filter_direct_comments(
    comments: list[dict[str, Any]],
    thread_id: str
) -> list[dict[str, Any]]:
    """
    Keep only direct comments on the hiring thread.
    """

    direct_comments = [
        comment
        for comment in comments
        if str(comment.get("parent_id")) == str(thread_id)
    ]

    logger.info(
        f"Filtered {len(direct_comments)} direct comments "
        f"from {len(comments)} total comments"
    )

    return direct_comments


def save_raw_comments(
    thread: dict[str, Any],
    comments: list[dict[str, Any]]
) -> None:
    """Save raw Hacker News thread and comments."""

    raw_data_dir = Path("data/raw")
    raw_data_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hackernews_{timestamp}.json"

    file_path = raw_data_dir / filename

    raw_data = {
        "thread": thread,
        "comments": comments
    }

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(raw_data, file, indent=4, ensure_ascii=False)

    logger.info(f"Saved {len(comments)} raw comments to {file_path}")



if __name__ == "__main__":

    thread = fetch_hiring_thread()

    if thread:
        thread_id = thread.get("objectID")

        print("\nHiring thread found!")
        print("Title:", thread.get("title"))
        print("Thread ID:", thread_id)
        print(
            "URL:",
            f"https://news.ycombinator.com/item?id={thread_id}"
        )

        comments = fetch_hiring_comments(thread_id)

        save_raw_comments(thread, comments)

        direct_comments = filter_direct_comments(comments, thread_id)

        print("\nTotal comments:", len(comments))
        print("Direct hiring comments:", len(direct_comments))

        print("\nFirst 5 direct comments:\n")

        for comment in direct_comments[:5]:
            print("Comment ID:", comment.get("objectID"))
            print("Author:", comment.get("author"))
            print("Text:", (comment.get("comment_text") or "")[:500])
            print("-" * 50)

        print("\nInspecting comment structure:\n")

        for comment in comments[:5]:
            print("Comment ID:", comment.get("objectID"))
            print("Parent ID:", comment.get("parent_id"))
            print("Thread ID:", comment.get("story_id"))
            print("Author:", comment.get("author"))
            print("-" * 40)

        print("\nTotal comments fetched:", len(comments))

        print("\nFirst 3 comments:\n")

        for comment in comments[:3]:
            print("Comment ID:", comment.get("objectID"))
            print("Author:", comment.get("author"))
            print("Text:", (comment.get("comment_text") or "")[:300])
            print("-" * 50)

    else:
        print("No hiring thread found.")