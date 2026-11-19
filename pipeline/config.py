
from pathlib import Path

# Main project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
LABELED_DATA_DIR = DATA_DIR / "labeled"
EXPORTS_DIR = DATA_DIR / "exports"

# Project settings
PROJECT_NAME = "Job Intelligence Pipeline"

# Scraping settings
REQUEST_DELAY = 1
MAX_RETRIES = 3
