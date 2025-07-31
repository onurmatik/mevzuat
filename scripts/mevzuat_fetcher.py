#!/usr/bin/env python3
"""
mevzuat_fetcher.py – mevzuat.gov.tr PDF arşivini indirir.

Kullanım:
    python mevzuat_fetcher.py 4                 # tüm order'lar
    python mevzuat_fetcher.py 4 7               # sadece order=7
    python mevzuat_fetcher.py 4 7 -n 15         # order=7, no=15'ten başlat
"""

import argparse
import itertools
import sys
import time
from pathlib import Path

import requests

URL_TMPL = "https://www.mevzuat.gov.tr/MevzuatMetin/{code}.{order}.{no}.pdf"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) "
        "Gecko/20100101 Firefox/115.0"
    ),
    "Accept": "application/pdf",
}

TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 0.3
MAX_CONSECUTIVE_MISSES = 20


def fetch_pdf(code: int, order: int, no: int, dest_root: Path) -> bool:
    url = URL_TMPL.format(code=code, order=order, no=no)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"⚠️  {url} istek hatası: {exc}", file=sys.stderr)
        return False

    if r.status_code == 200 and r.headers.get("Content-Type", "").lower().startswith("application/pdf"):
        out_dir = dest_root / f"{code}" / f"{order}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{code}.{order}.{no}.pdf"
        with open(out_file, "wb") as fp:
            fp.write(r.content)
        print(f"✓ {out_file.relative_to(dest_root)}")
        return True
    elif r.status_code == 404:
        return False
    else:
        print(f"⚠️  Beklenmeyen yanıt {r.status_code}: {url}", file=sys.stderr)
        return False


def crawl(code: int, dest_root: Path, order_start: int, no_start: int, single_order: bool) -> None:
    order_iter = [order_start] if single_order else itertools.count(start=order_start)
    print(f"▶️  Tarama başlıyor – CODE {code}, ORDER {order_start}{' (tek)' if single_order else '+'}, NO {no_start}+\n")

    for order in order_iter:
        consecutive_misses = 0
        found_any = False

        for no in itertools.count(start=no_start):
            ok = fetch_pdf(code, order, no, dest_root)
            time.sleep(SLEEP_BETWEEN_REQUESTS)

            if ok:
                consecutive_misses = 0
                found_any = True
            else:
                consecutive_misses += 1
                if consecutive_misses >= MAX_CONSECUTIVE_MISSES:
                    print(f"🔚  Order {order}: {MAX_CONSECUTIVE_MISSES} ardışık 404 – {'bitiriliyor' if single_order else 'sonraki order’a geçiliyor'}\n")
                    break

        if single_order or not found_any:
            if not found_any:
                print(f"🚩  CODE {code} için veri bulunamayan ilk ORDER {order}. Tarama bitti.")
            break
        no_start = 1  # sonraki order'larda no 1'den başlasın


def main() -> None:
    parser = argparse.ArgumentParser(description="mevzuat.gov.tr PDF arşivini indirir")
    parser.add_argument("code", type=int, help="CODE değeri")
    parser.add_argument("order", nargs="?", type=int, help="(Opsiyonel) ORDER değeri")
    parser.add_argument("-n", "--no-start", type=int, default=1, help="Başlangıç NO değeri (varsayılan: 1)")
    parser.add_argument("-o", "--output", default="mevzuat", help="Kök klasör (varsayılan: ./mevzuat)")
    args = parser.parse_args()

    dest_root = Path(args.output).resolve()
    crawl(
        code=args.code,
        dest_root=dest_root,
        order_start=args.order or 1,
        no_start=args.no_start,
        single_order=bool(args.order),
    )
    print("\n🎉  İşlem tamamlandı.")


if __name__ == "__main__":
    main()
