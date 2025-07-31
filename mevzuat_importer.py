#!/usr/bin/env python3
# -*- coding: utf‑8 -*-

"""
Import mevzuat.gov.tr metadata dumped to JSON into the Mevzuat Django model.

Usage
-----

    python import_mevzuat.py /path/to/mevzuat_kanun.json \
        --settings=myproject.settings

• The script is idempotent: it does an update‑or‑create on ``mevzuat_no``
  (re‑running it won’t create duplicates).
• Any unknown / missing dates are safely skipped.
• The whole import runs inside a single DB transaction.
"""

from pathlib import Path
import sys

# ../  →  project root that contains manage.py and the `mevzuat/` package
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path

import django
from django.db import transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str | None) -> _dt.date | None:
    """
    Convert strings like 24.07.2025, 9.7.25, 24/07/2025, 9/7/25  →  date.
    Returns None if the value is blank or un‑parsable (never raises).
    """
    if not value:
        return None

    value = value.strip()
    # Try dot‑ and slash‑separated patterns, 4‑digit and 2‑digit years
    for fmt in ("%d.%m.%Y", "%d.%m.%y",
                "%d/%m/%Y", "%d/%m/%y"):
        try:
            return _dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue  # try next format

    # Couldn’t parse; warn and fall back to None
    print(f"[WARN] Could not parse date: {value!r}", file=sys.stderr)
    return None

def _as_int(value: str | int | None, default: int = 0) -> int:
    """Cast to int or return *default* if impossible."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _bool_from_yesno(token: str | None) -> bool:
    return (token or "").upper().strip() == "EVET"


# ---------------------------------------------------------------------------
# Main import logic
# ---------------------------------------------------------------------------

def import_json(json_path: Path) -> None:
    from mevzuat.documents.models import Mevzuat

    with json_path.open(encoding="utf-8") as fp:
        records = json.load(fp)

    created, updated = 0, 0

    with transaction.atomic():
        for rec in records:
            defaults = dict(
                name                     = rec["mevAdi"],
                kabul_tarih              = _parse_date(rec["kabulTarih"]),
                resmi_gazete_sayisi      = rec["resmiGazeteSayisi"] or None,
                nitelik                  = rec["nitelik"],
                mukerrer                 = (rec["mukerrer"] or "").upper() == "EVET",
                tuzuk_mevzuat_tur        = rec["tuzukMevzuatTur"],
                has_old_law              = rec["hasOldLaw"],
            )

            obj, was_created = Mevzuat.objects.update_or_create(
                mevzuat_tur=rec["mevzuatTur"],
                mevzuat_tertib=_as_int(rec["mevzuatTertip"]),
                mevzuat_no=rec["mevzuatNo"],
                resmi_gazete_tarihi=_parse_date(rec["resmiGazeteTarihi"]),
                defaults=defaults,
            )
            created += was_created
            updated += (not was_created)

    print(f"✅  Import finished: {created} created, {updated} updated.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Import mevzuat JSON into DB")
    parser.add_argument("json_file", type=Path, help="Path to JSON dump")
    parser.add_argument(
        "--settings",
        default=os.getenv("DJANGO_SETTINGS_MODULE", "config.settings"),
        help="Django settings module (default: env DJANGO_SETTINGS_MODULE or 'config.settings')",
    )
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", args.settings)
    django.setup()

    import_json(args.json_file)


if __name__ == "__main__":
    main()
