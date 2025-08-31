#!/usr/bin/env python3
"""Temporary script to restore original metadata for existing documents.

The script reads JSON file(s) containing rows from the mevzuat.gov.tr
datatable endpoint and replaces the ``metadata`` field of matching
``Document`` instances with the original payload.  PDF files are
preserved and not re-downloaded.

Usage:
    python scripts/update_metadata.py path/to/metadata.json [more.json ...]
"""

from __future__ import annotations

import argparse
import json

# ---------------------------------------------------------------------------
# Bootstrap Django
# ---------------------------------------------------------------------------
from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mevzuat.settings")
import django

django.setup()

from mevzuat.documents.models import Document


def update_from_file(json_path: Path) -> tuple[int, int]:
    """Update documents from a JSON file.

    Parameters
    ----------
    json_path:
        Path to a JSON file containing a list of metadata dictionaries.

    Returns
    -------
    tuple[int, int]
        Number of documents updated and number of rows without a matching
        document.
    """

    data = json.loads(json_path.read_text(encoding="utf-8"))
    updated = 0
    skipped = 0

    for row in data:
        lookup = {
            "title": row.get("mevAdi"),
            "metadata__mevzuat_tur": int(row.get("mevzuatTur")),
            "metadata__mevzuat_tertib": int(row.get("mevzuatTertip")),
            "metadata__mevzuat_no": str(row.get("mevzuatNo")),
        }
        doc = Document.objects.filter(**lookup).first()
        if not doc:
            skipped += 1
            print(lookup)
            continue
        else:
            print(doc)

        doc.metadata = row
        doc.save()  # ``save`` updates the ``date`` field from metadata
        updated += 1

    return updated, skipped


def main(files: list[Path]) -> None:
    total_updated = 0
    total_skipped = 0
    for path in files:
        updated, skipped = update_from_file(path)
        total_updated += updated
        total_skipped += skipped
        print(f"{path}: {updated} updated, {skipped} missing")

    print(f"Total: {total_updated} updated, {total_skipped} missing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update Document metadata using original JSON payloads"
    )
    parser.add_argument(
        "json_files",
        nargs="+",
        type=Path,
        help="Path(s) to JSON file(s) containing document metadata",
    )
    args = parser.parse_args()
    main(args.json_files)
