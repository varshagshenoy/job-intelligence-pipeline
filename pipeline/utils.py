import logging
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests

# Create a logs directory
LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Create a reusable logger
logger = logging.getLogger("job_pipeline")

# Shared request safeguards
ROBOTS_CACHE = {}
LAST_REQUEST_TIME = {}

USER_AGENT = "JobIntelligencePipeline"


def wait_for_domain(url):
    """Ensure at least one second between requests to the same host."""
    domain = urlparse(url).netloc

    last_request = LAST_REQUEST_TIME.get(domain)

    if last_request is not None:
        elapsed = time.monotonic() - last_request
        remaining = 1 - elapsed

        if remaining > 0:
            time.sleep(remaining)

    LAST_REQUEST_TIME[domain] = time.monotonic()


def get_robots_parser(url):
    """Fetch and cache robots.txt rules for a host."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    if domain in ROBOTS_CACHE:
        return ROBOTS_CACHE[domain]

    robots_url = f"{parsed_url.scheme}://{domain}/robots.txt"

    wait_for_domain(robots_url)

    response = requests.get(
        robots_url,
        headers={"User-Agent": USER_AGENT},
        timeout=10
    )

    # A missing robots.txt (4xx) means no published restrictions.
    if response.status_code == 404:
        # No robots.txt file: no published restrictions.
        parser = RobotFileParser()
        parser.parse([])

    elif response.status_code >= 400:
        # Fail safely if access rules cannot be verified.
        raise RuntimeError(
            f"Could not verify robots.txt for {domain}: "
            f"HTTP {response.status_code}"
        )

    else:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())

    ROBOTS_CACHE[domain] = parser
    return parser


def polite_get(url, **kwargs):
    """Check robots.txt and rate-limit requests before fetching a URL."""
    parser = get_robots_parser(url)

    if not parser.can_fetch(USER_AGENT, url):
        raise PermissionError(
            f"robots.txt does not allow access to: {url}"
        )

    wait_for_domain(url)

    headers = kwargs.pop("headers", {})
    headers["User-Agent"] = USER_AGENT

    return requests.get(url, headers=headers, **kwargs)