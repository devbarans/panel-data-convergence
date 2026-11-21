"""Project paths shared by every pipeline step."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

OUTPUTS = ROOT / "outputs"
TABLES = OUTPUTS / "tables"
FIGURES = OUTPUTS / "figures"
RESULTS = OUTPUTS / "results.json"

REPORT = ROOT / "report" / "panel_data_report.pdf"

# Author details live in an untracked local file; see config/authors.example.json.
AUTHORS = ROOT / "config" / "authors.json"
