
import sqlite3
from pathlib import Path

from pipeline.config import DATA_DIR
from pipeline.utils import logger

import json
import hashlib
from datetime import datetime, timezone

from pipeline.dedup import get_dedup_key


# Store the database inside the project's data folder.
DATABASE_PATH = DATA_DIR / "jobs.db"


def get_connection():
    """
    Create and return a connection to the SQLite database.
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row

    return connection



def create_tables():
    """
    Create the jobs and job_history tables if they don't exist.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Main table: stores the latest version of each job.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_key TEXT UNIQUE NOT NULL,
            company TEXT,
            title TEXT,
            location TEXT,
            country TEXT,
            description TEXT,
            posted_at TEXT,
            source TEXT,
            source_id TEXT,
            url TEXT,
            source_urls TEXT,
            is_active INTEGER DEFAULT 1,
            first_seen TEXT,
            last_seen TEXT,
            job_data TEXT,
            extracted_data TEXT
        )
    """)

        # Add extracted_data to existing databases if it is missing.
    cursor.execute("PRAGMA table_info(jobs)")
    existing_columns = [
        column["name"] for column in cursor.fetchall()
    ]

    if "extracted_data" not in existing_columns:
        cursor.execute(
            "ALTER TABLE jobs ADD COLUMN extracted_data TEXT"
        )
        logger.info("Added extracted_data column to jobs table.")

    # History table: stores changes made to jobs.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    connection.commit()
    connection.close()

    logger.info("Database tables created successfully.")



def upsert_jobs(jobs):
    """
    Insert new jobs or update existing jobs.
    Record changes to important fields in job_history.
    """
    connection = get_connection()
    cursor = connection.cursor()

    current_time = datetime.now(timezone.utc).isoformat()

    tracked_fields = [
        "company",
        "title",
        "location",
        "description",
        "posted_at"
    ]

    inserted_count = 0
    updated_count = 0
    unchanged_count = 0

    for job in jobs:
        # Generate a stable key for identifying the job.
        key_parts = get_dedup_key(job)
        key_text = "|".join(key_parts)

        canonical_key = hashlib.sha256(
            key_text.encode("utf-8")
        ).hexdigest()

        source_urls = list(job.get("source_urls") or [])

        if job.get("url") and job["url"] not in source_urls:
            source_urls.append(job["url"])

        cursor.execute(
            "SELECT * FROM jobs WHERE canonical_key = ?",
            (canonical_key,)
        )

        existing = cursor.fetchone()

        job_json = json.dumps(job, ensure_ascii=False, default=str)
        source_urls_json = json.dumps(source_urls)

        if existing is None:
            # Insert a new job.
            cursor.execute("""
                INSERT INTO jobs (
                    canonical_key, company, title, location,
                    country, description, posted_at,
                    source, source_id, url, source_urls,
                    is_active, first_seen, last_seen, job_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (
                canonical_key,
                job.get("company"),
                job.get("title"),
                job.get("location"),
                job.get("country"),
                job.get("description"),
                job.get("posted_at"),
                job.get("source"),
                job.get("source_id"),
                job.get("url"),
                source_urls_json,
                current_time,
                current_time,
                job_json
            ))

            inserted_count += 1

        else:

            # Merge previously stored URLs with newly discovered URLs.
            existing_urls = json.loads(existing["source_urls"] or "[]")

            for url in existing_urls:
                if url not in source_urls:
                    source_urls.append(url)

            source_urls_json = json.dumps(source_urls)


            # Compare important fields with the existing record.
            changes = []

            for field in tracked_fields:
                old_value = existing[field]
                new_value = job.get(field)

                # Don't overwrite an existing value with missing data.
                if new_value is not None and new_value != old_value:
                    changes.append((field, old_value, new_value))

            for field, old_value, new_value in changes:
                cursor.execute("""
                    INSERT INTO job_history (
                        job_id, field_name, old_value,
                        new_value, changed_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    existing["id"],
                    field,
                    str(old_value) if old_value is not None else None,
                    str(new_value),
                    current_time
                ))

            # Update the latest job record.
            cursor.execute("""
                UPDATE jobs
                SET company = COALESCE(?, company),
                    title = COALESCE(?, title),
                    location = COALESCE(?, location),
                    country = COALESCE(?, country),
                    description = COALESCE(?, description),
                    posted_at = COALESCE(?, posted_at),
                    source_urls = ?,
                    is_active = 1,
                    last_seen = ?,
                    job_data = ?
                WHERE id = ?
            """, (
                job.get("company"),
                job.get("title"),
                job.get("location"),
                job.get("country"),
                job.get("description"),
                job.get("posted_at"),
                source_urls_json,
                current_time,
                job_json,
                existing["id"]
            ))

            if changes:
                updated_count += 1
            else:
                unchanged_count += 1

    connection.commit()
    connection.close()

    logger.info("New jobs inserted: %s", inserted_count)
    logger.info("Existing jobs updated: %s", updated_count)
    logger.info("Unchanged jobs: %s", unchanged_count)

    return {
        "inserted": inserted_count,
        "updated": updated_count,
        "unchanged": unchanged_count
    }



def upsert_extractions(extracted_records):
    connection = get_connection()
    cursor = connection.cursor()

    updated_count = 0
    unmatched_count = 0

    for record in extracted_records:
        original_job = record.get("original_job", {})
        extracted_data = record.get("extracted_data", {})

        key_parts = get_dedup_key(original_job)
        key_text = "|".join(key_parts)
        canonical_key = hashlib.sha256(
            key_text.encode("utf-8")
        ).hexdigest()

        extracted_json = json.dumps(
            extracted_data,
            ensure_ascii=False
        )

        cursor.execute(
            """
            UPDATE jobs
            SET extracted_data = ?
            WHERE canonical_key = ?
            """,
            (extracted_json, canonical_key)
        )

        if cursor.rowcount > 0:
            updated_count += 1
        else:
            unmatched_count += 1

    connection.commit()
    connection.close()

    logger.info(
        "Extraction data linked to %s database records.",
        updated_count
    )
    if unmatched_count:
        logger.warning(
            "%s extracted records did not match database jobs.",
            unmatched_count
        )

    return updated_count
