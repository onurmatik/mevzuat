#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fetch the first page of results from
https://www.mevzuat.gov.tr/Anasayfa/MevzuatDatatable and dump to JSON.

This version **automates** antiforgery token handling and stops after the first
page-size batch of rows.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import requests

URL = "https://www.mevzuat.gov.tr/Anasayfa/MevzuatDatatable"
HOMEPAGE = "https://www.mevzuat.gov.tr/"

BASE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json; charset=UTF-8",
    "Origin": "https://www.mevzuat.gov.tr",
    "Referer": "https://www.mevzuat.gov.tr/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}

DEFAULT_PARAMETERS = {
    "MevzuatTur": "Teblig",
    "YonetmelikMevzuatTur": "OsmanliKanunu",
    "AranacakIfade": "",
    "AranacakYer": "2",
    "MevzuatNo": "",
    "BaslangicTarihi": "",
    "BitisTarihi": "",
}


def find_antiforgery_cookie(cookies: requests.cookies.RequestsCookieJar):
    for c in cookies:
        if c.name.startswith(".AspNetCore.Antiforgery"):
            return c.value
    raise RuntimeError("Antiforgery cookie not found.")


def bootstrap_session(timeout: int = 30):
    sess = requests.Session()
    r = sess.get(HOMEPAGE, headers=BASE_HEADERS, timeout=timeout)
    r.raise_for_status()
    anti_token = find_antiforgery_cookie(sess.cookies)
    return sess, anti_token


def build_body(parameters: dict):
    return {
        "columns": [
            {"data": None, "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
            {"data": None, "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
            {"data": None, "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
        ],
        "order": [],
        "search": {"value": "", "regex": False},
        "parameters": parameters,
    }


def fetch_first_page(mevzuat_tur: str, page_size: int, outfile: Path, extra_params: dict | None = None):
    session, anti_token = bootstrap_session()
    params = {**DEFAULT_PARAMETERS, **(extra_params or {}), "MevzuatTur": mevzuat_tur, "antiforgerytoken": anti_token}
    body = build_body(params)
    body.update({"draw": 1, "start": 0, "length": page_size})

    resp = session.post(URL, headers=BASE_HEADERS, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("data", [])

    outfile.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(rows)} rows and saved to {outfile.resolve()}")


def parse_args():
    p = argparse.ArgumentParser(description="Fetch first page from mevzuat.gov.tr datatable.")
    p.add_argument("--mevzuat-tur", default="Teblig", help="Value for parameters.MevzuatTur")
    p.add_argument("--page-size", type=int, default=200, help="Page size to fetch")
    p.add_argument("--outfile", type=Path, default=Path("mevzuat_firstpage.json"), help="Output JSON path")
    p.add_argument("--extra-params", type=str, default="{}", help="JSON dict merged into parameters")
    return p.parse_args()


def main():
    args = parse_args()
    try:
        extra_params = json.loads(args.extra_params)
        if not isinstance(extra_params, dict):
            raise ValueError("--extra-params must be a JSON object")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON for --extra-params: {e}")

    fetch_first_page(args.mevzuat_tur, args.page_size, args.outfile, extra_params)


if __name__ == "__main__":
    main()
