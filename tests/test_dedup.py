
from pipeline.dedup import deduplicate_jobs


def test_duplicate_jobs_are_removed():
    jobs = [
        {
            "company": "Stripe",
            "title": "Data Engineer",
            "location": "New York",
            "source": "greenhouse",
            "url": "https://example.com/job1"
        },
        {
            "company": "Stripe",
            "title": "Data Engineer",
            "location": "New York",
            "source": "hackernews",
            "url": "https://example.com/job2"
        }
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 1


def test_source_urls_are_preserved():
    jobs = [
        {
            "company": "Stripe",
            "title": "Data Engineer",
            "location": "New York",
            "source": "greenhouse",
            "url": "https://example.com/job1"
        },
        {
            "company": "Stripe",
            "title": "Data Engineer",
            "location": "New York",
            "source": "hackernews",
            "url": "https://example.com/job2"
        }
    ]

    result = deduplicate_jobs(jobs)

    assert len(result[0]["source_urls"]) == 2


def test_different_jobs_are_not_removed():
    jobs = [
        {
            "company": "Stripe",
            "title": "Data Engineer",
            "location": "New York",
            "url": "https://example.com/job1"
        },
        {
            "company": "Stripe",
            "title": "Analytics Engineer",
            "location": "New York",
            "url": "https://example.com/job2"
        }
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 2


def test_text_formatting_differences_are_handled():
    jobs = [
        {
            "company": "Stripe",
            "title": "Data Engineer",
            "location": "New York",
            "url": "https://example.com/job1"
        },
        {
            "company": " STRIPE ",
            "title": "DATA ENGINEER",
            "location": "NEW YORK",
            "url": "https://example.com/job2"
        }
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 1
