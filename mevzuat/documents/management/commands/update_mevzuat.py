from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

import requests
from requests.adapters import HTTPAdapter
from requests.cookies import create_cookie
from requests.exceptions import ReadTimeout, RequestException
from urllib3.util.retry import Retry

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import Document, DocumentType


BASE_URL = "https://www.mevzuat.gov.tr/"
DATA_URL = "https://www.mevzuat.gov.tr/Anasayfa/MevzuatDatatable"

POST_HEADERS_BASE = {
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

GET_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": POST_HEADERS_BASE["Accept-Language"],
    "User-Agent": POST_HEADERS_BASE["User-Agent"],
    "Referer": "https://www.mevzuat.gov.tr/",
}

PAGE_SIZE_DEFAULT = 20

COMMON_BODY_TEMPLATE: dict[str, Any] = {
    "columns": [
        {"data": None, "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
        {"data": None, "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
        {"data": None, "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
    ],
    "order": [],
    "search": {"value": "", "regex": False},
    "parameters": {
        "MevzuatTur": "",
        "YonetmelikMevzuatTur": "OsmanliKanunu",
        "AranacakIfade": "",
        "AranacakYer": "2",
        "MevzuatNo": "",
        "BaslangicTarihi": "",
        "BitisTarihi": "",
        "antiforgerytoken": "",
    },
}

DATE_KEYS_RG = [
    "ResmiGazeteTarihi", "ResmiGazeteYayinTarihi", "RG_Tarihi", "YayinTarihi",
]
DATE_KEYS_KABUL = [
    "KabulTarihi", "KabulTarih", "Kabul",
]


# ---------------- utils ----------------

def _dbg(opts: dict, msg: str) -> None:
    if opts.get("debug"):
        print(f"[debug] {msg}")


def _safe_json(resp: requests.Response) -> dict[str, Any]:
    ctype = (resp.headers.get("content-type") or "").lower()
    if "json" not in ctype:
        text = (resp.text or "")[:300].replace("\n", " ").replace("\r", " ")
        raise CommandError(f"Non-JSON (type={ctype or 'unknown'}): {text!r}")
    text = resp.text or ""
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    if text.startswith(")]}',"):
        nl = text.find("\n")
        text = text[nl + 1 :] if nl >= 0 else ""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        snippet = text[:300].replace("\n", " ").replace("\r", " ")
        raise CommandError(f"JSON decode error: {e}; body starts {snippet!r}")


def _parse_date(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, str) and value.startswith("/Date(") and value.endswith(")/"):
        try:
            ts = int(value[6:-2]) / 1000.0
            return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            return None
    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(float(value) / 1000.0).strftime("%Y-%m-%d")
        except Exception:
            return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value)[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _first_int(*vals, default: Optional[int] = None) -> Optional[int]:
    for v in vals:
        if v is None:
            continue
        try:
            return int(v)
        except (TypeError, ValueError):
            continue
    return default


def _extract_ids_from_urls(row: dict[str, Any]) -> tuple[Optional[int], Optional[int], Optional[str]]:
    for v in row.values():
        if not isinstance(v, str):
            continue
        if "MevzuatNo=" in v and ("MevzuatTur=" in v or "MevzuatTertip=" in v):
            try:
                qs = urlparse(v).query
                params = parse_qs(qs)
                mev_no = (params.get("MevzuatNo") or [None])[0]
                mev_tur = _first_int((params.get("MevzuatTur") or [None])[0])
                mev_tertib = _first_int((params.get("MevzuatTertip") or [None])[0])
                return mev_tur, mev_tertib, mev_no
            except Exception:
                continue
    return None, None, None


def _strip_tags(s: str) -> str:
    # remove tags and collapse whitespace
    txt = re.sub(r"<[^>]+>", " ", s)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _extract_title_from_values(row: dict[str, Any]) -> Optional[str]:
    # Try common keys first
    for key in (
        "Baslik", "MevzuatBaslik", "MevzuatAdi", "Adi", "Name", "KisaBaslik",
        "BaslikText", "DetayBaslik", "UzunBaslik", "Basligi",
    ):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return _strip_tags(val)

    # Otherwise scan any string-ish field for a long, meaningful text
    candidates: list[str] = []
    for v in row.values():
        if isinstance(v, str):
            t = _strip_tags(v)
            if len(t) >= 30:
                candidates.append(t)

    # Prefer ones that look like law/KHK headings
    def score(s: str) -> tuple[int, int]:
        s_up = s.upper()
        hits = sum(w in s_up for w in ("KANUN", "KARARNAME", "KHK", "CUMHURBAŞKANLIĞI", "ANAYASA"))
        return (hits, len(s))  # more hits, longer better

    if candidates:
        best = max(candidates, key=score)
        # avoid accidentally returning a URL or numeric string
        if any(ch.isalpha() for ch in best):
            return best

    return None


def _fetch_title_from_detail(session: requests.Session, md: dict[str, Any], referer_url: str, timeout: tuple[int, int], opts: dict) -> Optional[str]:
    """
    Fetch the detail HTML and try to pull an H1/H2 or <title>.
    Example URL pattern observed publicly:
        /Mevzuat?MevzuatNo=703&MevzuatTur=4&MevzuatTertip=5
    """
    try:
        mev_no = md.get("mevzuat_no")
        mev_tur = md.get("mevzuat_tur")
        mev_tertib = md.get("mevzuat_tertib")
        if not (mev_no and mev_tur and mev_tertib):
            return None

        url = f"{BASE_URL}Mevzuat?MevzuatNo={mev_no}&MevzuatTur={mev_tur}&MevzuatTertip={mev_tertib}"
        headers = dict(GET_HEADERS)
        headers["Referer"] = referer_url
        r = session.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        html = r.text or ""

        # H1/H2 first
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if not m:
            m = re.search(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE | re.DOTALL)
        if m:
            t = _strip_tags(m.group(1))
            if t:
                _dbg(opts, f"title from detail h-tag: {t[:80]}…")
                return t

        # Fallback: page title
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            t = _strip_tags(m.group(1))
            if t:
                _dbg(opts, f"title from <title>: {t[:80]}…")
                return t

    except Exception as e:
        _dbg(opts, f"title detail fetch failed: {e}")

    return None


def _best_title(row: dict[str, Any], md: dict[str, Any], session: requests.Session, referer_url: str, timeout: tuple[int, int], opts: dict) -> str:
    t = _extract_title_from_values(row)
    if t:
        return t
    t = _fetch_title_from_detail(session, md, referer_url, timeout, opts)
    if t:
        return t
    # Final fallback
    return str(md.get("mevzuat_no") or "").strip() or "Untitled"


def _extract_rg_sayisi_and_mukerrer(row: dict[str, Any]) -> tuple[Optional[str], bool]:
    rg = row.get("ResmiGazeteSayisi") or row.get("RGSayisi")
    if not isinstance(rg, str):
        return None, False
    s = rg.strip()
    lower = s.lower()
    muk = ("mükerrer" in lower) or ("mukerrer" in lower) or ("m\u00fckerrer" in lower)
    return s, muk


def _extract_has_old_law(row: dict[str, Any]) -> bool:
    for key in ("HasOldLaw", "MulgaKanunVar", "MülgaKanunVar", "EskiMevzuatVar", "EskiMevzuat"):
        if key in row:
            v = row.get(key)
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v != 0
            if isinstance(v, str):
                s = v.strip().lower()
                return s in {"1", "true", "evet", "var", "yes"}
    return False


def _extract_rg_date(row: dict[str, Any]) -> Optional[str]:
    # 1) known key names
    for key in DATE_KEYS_RG:
        if key in row:
            d = _parse_date(row.get(key))
            if d:
                return d
    # 2) heuristic keys like *resmi*gazete* + *tarih*
    for k, v in row.items():
        if not isinstance(v, (str, int, float)):
            continue
        kl = str(k).lower()
        if (("resmi" in kl or "rg" in kl) and "gazete" in kl and "tarih" in kl) or ("yayin" in kl and "tarih" in kl):
            d = _parse_date(v)
            if d:
                return d
    # 3) last resort: scan values that parse as date
    for v in row.values():
        if isinstance(v, (str, int, float)):
            d = _parse_date(v)
            if d:
                return d
    return None


def _extract_kabul_date(row: dict[str, Any]) -> Optional[str]:
    for key in DATE_KEYS_KABUL:
        if key in row:
            d = _parse_date(row.get(key))
            if d:
                return d
    return None


def _row_to_metadata(row: dict[str, Any]) -> dict[str, Any]:
    mev_tur = _first_int(row.get("MevzuatTur"), row.get("Tur"), row.get("MevzuatTurId"))
    mev_tertib = _first_int(row.get("MevzuatTertip"), row.get("MevzuatTertib"))
    mev_no = row.get("MevzuatNo") or row.get("No")

    if mev_tur is None or mev_tertib is None or not mev_no:
        t2, tert2, no2 = _extract_ids_from_urls(row)
        if mev_tur is None:
            mev_tur = t2
        if mev_tertib is None:
            mev_tertib = tert2
        if not mev_no:
            mev_no = no2

    rg_date = _extract_rg_date(row)
    kabul = _extract_kabul_date(row)
    rg_sayisi, mukerrer = _extract_rg_sayisi_and_mukerrer(row)

    md: dict[str, Any] = {
        "mevzuat_no": str(mev_no) if mev_no is not None else None,
        "mevzuat_tertib": mev_tertib if mev_tertib is not None else 5,
        "kabul_tarih": kabul,                 # keep key even if None
        "resmi_gazete_tarihi": rg_date,      # required for creation
        "resmi_gazete_sayisi": rg_sayisi,    # keep key even if None
        "nitelik": row.get("Nitelik"),
        "mukerrer": bool(mukerrer),
        "tuzuk_mevzuat_tur": _first_int(row.get("TuzukMevzuatTur"), default=0),
        "has_old_law": _extract_has_old_law(row),
        "mevzuat_tur": _first_int(mev_tur, default=None),
    }
    return md


def _load_cookies_into_jar(session: requests.Session, cookie_str: str) -> int:
    count = 0
    parts = [p.strip() for p in (cookie_str or "").split(";")]
    for p in parts:
        if not p or "=" not in p:
            continue
        name, value = p.split("=", 1)
        name, value = name.strip(), value.strip()
        if not name:
            continue
        ck = create_cookie(name=name, value=value, domain="www.mevzuat.gov.tr", path="/")
        session.cookies.set_cookie(ck)
        count += 1
    return count


def _infer_antiforgery_from_jar(session: requests.Session) -> Optional[str]:
    for c in session.cookies:
        if ("Antiforgery" in c.name) or ("RequestVerification" in c.name):
            return c.value
    return None


def _bootstrap_session(session: requests.Session, timeout: tuple[int, int]) -> None:
    for path in ("", "Anasayfa"):
        r = None
        try:
            r = session.get(f"{BASE_URL}{path}", headers=GET_HEADERS, timeout=timeout, stream=True)
            r.raise_for_status()
        finally:
            try:
                if r is not None:
                    r.close()
            except Exception:
                pass


@dataclass
class PageGuard:
    last_keys: Optional[frozenset] = None
    repeats: int = 0

    def update(self, page_keys: frozenset) -> None:
        if self.last_keys == page_keys:
            self.repeats += 1
        else:
            self.last_keys = page_keys
            self.repeats = 0


# ---------------- command ----------------

class Command(BaseCommand):
    help = "Fetch mevzuat rows for a given DocumentType slug and create records (no PDF downloads yet)."

    def add_arguments(self, parser):
        parser.add_argument("slug", help="Document type slug (e.g. 'kanun')")

        # Fetch tuning
        parser.add_argument("--limit", type=int, default=None, help="Max documents to create")
        parser.add_argument("--timeout", type=int, default=60, help="Read timeout (seconds)")
        parser.add_argument("--pagesize", type=int, default=PAGE_SIZE_DEFAULT, help="Page size (server accepts 10..200)")
        parser.add_argument("--sleep", type=float, default=0.6, help="Pause between page requests (seconds)")
        parser.add_argument("--max_pages", type=int, default=200, help="Hard cap on page count (anti-loop guard)")

        # Session / CSRF
        parser.add_argument("--cookie-header", help="Verbatim Cookie header string to send on every POST")
        parser.add_argument("--cookies", help="Cookie jar string 'a=b; c=d; ...' to load into session")
        parser.add_argument("--antiforgery", help="Explicit antiforgery token to use")
        parser.add_argument("--referer", default="/", help="Referer path or URL (default '/')")

        # Debug
        parser.add_argument("--debug", action="store_true", help="Verbose debug logging")

    def handle(self, *args, **opts):
        slug: str = opts["slug"]
        limit: Optional[int] = opts["limit"]
        read_timeout: int = int(opts["timeout"])
        page_size: int = max(1, int(opts["pagesize"]))
        pause: float = float(opts["sleep"])
        max_pages: int = int(opts["max_pages"])

        cookie_header: Optional[str] = opts.get("cookie_header")
        cookie_jar_str: Optional[str] = opts.get("cookies")
        antiforgery_opt: Optional[str] = opts.get("antiforgery")
        referer_opt: str = opts.get("referer") or "/"
        referer_url = referer_opt if referer_opt.startswith("http") else (BASE_URL.rstrip("/") + "/" + referer_opt.lstrip("/"))

        try:
            doc_type = DocumentType.objects.get(slug=slug)
        except DocumentType.DoesNotExist as exc:
            raise CommandError(f"Unknown document type slug: {slug}") from exc

        if not doc_type.short_name:
            raise CommandError("DocumentType.short_name is required (used as MevzuatTur filter).")

        # Resilient session
        session = requests.Session()
        retry = Retry(
            total=6, connect=3, read=3, backoff_factor=1.2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods={"GET", "POST", "HEAD"},
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))

        token: Optional[str] = antiforgery_opt

        # Load cookies (either explicit header or jar)
        use_cookie_header = False
        if cookie_header:
            use_cookie_header = True
            _dbg(opts, "using verbatim Cookie header")
        elif cookie_jar_str:
            n = _load_cookies_into_jar(session, cookie_jar_str)
            _dbg(opts, f"loaded {n} cookies into session; token set? {bool(token)}")

        # If no token provided, try to infer from jar; otherwise bootstrap first
        if not token and not use_cookie_header:
            token = _infer_antiforgery_from_jar(session)
            if not token:
                _bootstrap_session(session, timeout=(10, read_timeout))
                token = _infer_antiforgery_from_jar(session)
        if use_cookie_header and not token:
            raise CommandError("--cookie-header requires --antiforgery token (cannot infer from header string).")

        # Ready to page
        created = 0
        seen_total = 0
        skipped_existing = 0
        skipped_invalid = 0
        skipped_no_date = 0

        self.stdout.write(self.style.HTTP_INFO(
            f"Fetching '{doc_type.name}' (MevzuatTur={doc_type.short_name}) page_size={page_size}"
        ))

        start = 0
        draw = 1
        pages = 0
        guard = PageGuard()

        # track overall seen keys to detect loops and avoid infinite crawling
        all_seen_keys: set[tuple[str, int]] = set()

        timeout = (10, read_timeout)

        while True:
            pages += 1
            if pages > max_pages:
                raise CommandError(f"Reached --max_pages={max_pages} without finishing; stopping to avoid loops.")

            body = deepcopy(COMMON_BODY_TEMPLATE)
            body["parameters"]["MevzuatTur"] = doc_type.short_name
            body["parameters"]["antiforgerytoken"] = token or ""
            body.update({"draw": draw, "start": start, "length": page_size})

            headers = dict(POST_HEADERS_BASE)
            headers["Referer"] = referer_url
            headers["RequestVerificationToken"] = token or ""
            if use_cookie_header:
                headers["Cookie"] = cookie_header

            _dbg(opts, f"POST headers (subset): {{'Referer': '{headers['Referer']}', 'Cookie': {bool(headers.get('Cookie'))}, 'RequestVerificationToken': {bool(headers.get('RequestVerificationToken'))}}}")
            _dbg(opts, f"POST body.parameters: {json.dumps(body.get('parameters', {}), ensure_ascii=False)}")

            # perform request with HTML recovery (jar mode only)
            html_retries = 0
            while True:
                try:
                    resp = session.post(DATA_URL, headers=headers, json=body, timeout=timeout)
                    ctype = (resp.headers.get("content-type") or "").lower()
                    _dbg(opts, f"POST {DATA_URL} -> {resp.status_code} ctype={ctype or 'unknown'} len={len(resp.content) if resp.content is not None else 0}")
                    if opts.get("debug"):
                        _dbg(opts, f"resp headers: {json.dumps({k.lower(): v for k,v in resp.headers.items() if k.lower() in ('content-type','set-cookie')}, ensure_ascii=False)}")
                    resp.raise_for_status()
                    payload = _safe_json(resp)
                    break
                except CommandError as e:
                    if use_cookie_header:
                        raise
                    if "Non-JSON" in str(e) and html_retries < 2:
                        html_retries += 1
                        _dbg(opts, f"HTML received; attempting session refresh #{html_retries}")
                        _bootstrap_session(session, timeout=timeout)
                        token = _infer_antiforgery_from_jar(session) or token
                        headers["RequestVerificationToken"] = token or ""
                        time.sleep(pause)
                        continue
                    raise
                except ReadTimeout as e:
                    self.stderr.write(self.style.WARNING(
                        f"Read timeout at start={start}, draw={draw}; retrying… ({e})"
                    ))
                    time.sleep(min(3.0, pause))
                    continue
                except RequestException as e:
                    raise CommandError(f"Request failed: {e}") from e

            # parse rows
            rows = payload.get("data") or payload.get("aaData") or []
            total = payload.get("recordsFiltered") or payload.get("recordsTotal")
            try:
                total = int(total) if total is not None else None
            except Exception:
                total = None

            _dbg(opts, f"[page] start={start} draw={draw} rows={len(rows)} total={total or '-'} created={created}")

            if not rows:
                break

            page_keys: set[tuple[str, int]] = set()
            for row in rows:
                md_tmp = _row_to_metadata(row)
                mev_no_tmp = md_tmp.get("mevzuat_no")
                mev_tertib_tmp = md_tmp.get("mevzuat_tertib") or 5
                key_tmp = (str(mev_no_tmp) if mev_no_tmp else "", int(mev_tertib_tmp))
                page_keys.add(key_tmp)

            guard.update(frozenset(page_keys))
            if guard.repeats >= 2:
                raise CommandError("Server returned the same page repeatedly; stopping to avoid infinite loop.")

            for row in rows:
                seen_total += 1
                md = _row_to_metadata(row)

                if not md.get("mevzuat_no"):
                    skipped_invalid += 1
                    continue

                # de-dupe within run
                key = (md["mevzuat_no"], md["mevzuat_tertib"])
                if key in all_seen_keys:
                    continue
                all_seen_keys.add(key)

                # DB de-dupe first (so DB is “seen” even if date fails)
                if Document.objects.filter(
                    type=doc_type,
                    metadata__mevzuat_no=md["mevzuat_no"],
                    metadata__mevzuat_tertib=md["mevzuat_tertib"],
                ).exists():
                    skipped_existing += 1
                    continue

                # require RG date
                if not md.get("resmi_gazete_tarihi"):
                    skipped_no_date += 1
                    if opts.get("debug"):
                        _dbg(opts, f"no RG date for {key}; row keys: {list(row.keys())}")
                    continue

                title = _best_title(row, md, session, referer_url, timeout, opts)

                with transaction.atomic():
                    Document.objects.create(
                        type=doc_type,
                        title=title,
                        metadata=md,
                    )
                    created += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Created {doc_type}: {title} metadata: {md}"
                    ))

                if limit and created >= limit:
                    self.stdout.write(self.style.SUCCESS(
                        f"Created {created} new documents (limit reached). "
                        f"Seen={seen_total}, skipped_existing={skipped_existing}, "
                        f"skipped_invalid={skipped_invalid}, skipped_no_date={skipped_no_date}"
                    ))
                    return

            # advance or finish
            if total is not None:
                next_start = start + page_size
                if next_start >= max(total, start + len(rows)):
                    break
                start = next_start
            else:
                if len(rows) < page_size:
                    break
                start += page_size

            draw += 1
            if pause:
                time.sleep(pause)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created={created}, Seen={seen_total}, "
            f"Skipped(existing)={skipped_existing}, Skipped(invalid)={skipped_invalid}, "
            f"Skipped(no-date)={skipped_no_date}"
        ))
