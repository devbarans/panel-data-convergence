"""Read the cover details (authors, course, date) from the local config file.

The file config/authors.json is not tracked by git so personal details stay out of the
repository. Copy config/authors.example.json to config/authors.json and fill it in.
Without the file the cover is printed with empty fields.
"""
import json

from paths import AUTHORS


def load_authors() -> dict:
    if not AUTHORS.exists():
        return {"course": "", "date": "", "authors": []}
    data = json.loads(AUTHORS.read_text(encoding="utf-8"))
    return {
        "course": data.get("course", ""),
        "date": data.get("date", ""),
        "authors": [(a.get("name", ""), a.get("student_id", "")) for a in data.get("authors", [])],
    }
