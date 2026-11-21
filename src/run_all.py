"""Run the whole analysis pipeline: data -> models -> figures -> report.

Usage (from the repository root):  python src/run_all.py
To rebuild the slides afterwards:   npm install && npm run slides
"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
STEPS = ["prepare_data.py", "models.py", "figures.py", "build_report.py"]

for step in STEPS:
    print(f"\n=== {step} ===")
    result = subprocess.run([sys.executable, str(SRC / step)])
    if result.returncode != 0:
        sys.exit(result.returncode)
print("\nDone. Outputs: outputs/, report/panel_data_report.pdf")
