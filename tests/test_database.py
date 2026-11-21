import pytest
import pipeline.database as database
import json

@pytest.fixture
def temp_database(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_jobs.db"
    monkeypatch.setattr(database, "DATABASE_PATH", test_db_path)
    database.create_tables()

import sqlite3

from pipeline.database import (
    create_tables,
    get_connection,
    upsert_jobs,
)


def test_job_changes_are_recorded(temp_database):

    job = {
        "company": "Test Company",
        "title": "Data Engineer",
        "location": "New York, US",
        "description": "Original job description",
        "posted_at": "2026-11-20",
        "source": "test",
        "source_id": "test-123",
        "url": "https://example.com/job/123",
    }

    # Insert the original job.
    upsert_jobs([job])

    # Change its description.
    updated_job = job.copy()
    updated_job["description"] = "Updated job description"

    # Upsert the modified job.
    upsert_jobs([updated_job])

    connection = get_connection()

    history = connection.execute(
        """
        SELECT field_name, old_value, new_value
        FROM job_history
        WHERE field_name = 'description'
        """
    ).fetchall()

    connection.close()

    assert len(history) == 1
    assert history[0]["old_value"] == "Original job description"
    assert history[0]["new_value"] == "Updated job description"



def test_source_urls_are_preserved(temp_database):

    job = {
        "company": "Test Company",
        "title": "Data Engineer",
        "location": "New York, US",
        "description": "Job description",
        "source": "test",
        "source_id": "test-456",
        "url": "https://example.com/job/123"
    }

    # Insert the original job.
    upsert_jobs([job])

    # Update the same job with a different source URL.
    updated_job = job.copy()
    updated_job["url"] = "https://another-source.com/job/456"

    upsert_jobs([updated_job])

    connection = get_connection()

    result = connection.execute(
        "SELECT source_urls FROM jobs"
    ).fetchone()

    connection.close()

    saved_urls = json.loads(result["source_urls"])

    assert "https://example.com/job/123" in saved_urls
    assert "https://another-source.com/job/456" in saved_urls
    assert len(saved_urls) == 2
