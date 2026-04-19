"""
storage/exporter.py
───────────────────
Export leads to CSV.

Design:
  - Column order is explicit and human-friendly (most important fields first).
  - Phone is formatted as readable (555) 555-5555 in the export.
  - Dates are formatted as YYYY-MM-DD for spreadsheet compatibility.
  - All None values become empty strings.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from storage.schema import Lead


# Ordered list of (csv_column_name, lead_attribute_or_callable)
EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("ID",               "id"),
    ("Teacher Name",     "teacher_name"),
    ("Studio Name",      "studio_name"),
    ("Phone",            "phone"),
    ("Email",            "email"),
    ("Website",          "website"),
    ("Address",          "address"),
    ("ZIP",              "zip_code"),
    ("Territory",        "territory"),
    ("Source",           "source"),
    ("Status",           "status"),
    ("Assigned To",      "assigned_to"),
    ("Rating",           "rating"),
    ("Reviews",          "review_count"),
    ("Most Recent Review", "most_recent_review"),
    ("Photos",           "photo_count"),
    ("Domain Age (days)","domain_age_days"),
    ("Domain Created",   "domain_created"),
    ("Confidence Score", "confidence_score"),
    ("Notes",            "notes"),
    ("Sources (all)",    "sources"),
    ("Found At",         "found_at"),
    ("Updated At",       "updated_at"),
    ("Google Place ID",  "google_place_id"),
]


def export_to_csv(
    leads: list[Lead],
    output_path: str | Path,
    include_taken: bool = False,
) -> int:
    """
    Write leads to a CSV file.

    Args:
        leads:         List of Lead objects to export.
        output_path:   File path for the CSV output.
        include_taken: If False (default), skip leads with status=taken.

    Returns:
        Number of rows written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not include_taken:
        leads = [l for l in leads if l.status.value != "taken"]

    rows_written = 0

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[col for col, _ in EXPORT_COLUMNS])
        writer.writeheader()

        for lead in leads:
            row = {}
            for col_name, attr in EXPORT_COLUMNS:
                row[col_name] = _format_field(lead, attr)
            writer.writerow(row)
            rows_written += 1

    logger.info(f"Exported {rows_written} leads to {output_path}")
    return rows_written


# ─────────────────────────────────────────────
# Field formatters
# ─────────────────────────────────────────────

def _format_field(lead: Lead, attr: str) -> str:
    """Get a field value from a lead and format it for CSV output."""
    val = getattr(lead, attr, None)

    if val is None:
        return ""

    # Enum → string value
    if hasattr(val, "value"):
        return str(val.value)

    # List of enums (sources list)
    if isinstance(val, list):
        return ", ".join(
            item.value if hasattr(item, "value") else str(item)
            for item in val
        )

    # Phone → readable format
    if attr == "phone" and isinstance(val, str) and len(val) == 10:
        return f"({val[:3]}) {val[3:6]}-{val[6:]}"

    # Datetimes → YYYY-MM-DD
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")

    return str(val)
