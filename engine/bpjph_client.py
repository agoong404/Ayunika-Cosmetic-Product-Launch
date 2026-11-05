"""
bpjph_client.py — klien pencarian sertifikat halal publik BPJPH.

Sumber: https://bpjph.halal.go.id/cari/sertifikat?produk=&produsen=&no_regis=&page=
Halaman ini di-render server-side, jadi datanya bisa diambil tanpa browser.

Status: TIDAK RESMI / TIDAK TERDOKUMENTASI.
  - Bukan API publik resmi. Bisa berubah atau diblokir kapan saja.
  - Pakai cache + jeda antar permintaan. Jangan dijadikan backend produksi
    tanpa izin BPJPH.

Batas data yang tersedia (penting, baca sebelum mendesain produk):
  ✔ nama produk, merek dagang, pelaku usaha, alamat pabrik, nomor sertifikat,
    tanggal terbit, skala usaha, foto produk
  ✘ TIDAK ada: barcode, komposisi bahan, tanggal berlaku/kedaluwarsa, cakupan bahan
  → "tidak ditemukan" BUKAN berarti tidak halal.

Cara pakai yang benar (penting):
  Pencarian bersifat SUBSTRING lintas field. Kata tunggal menghasilkan himpunan besar yang
  bercampur — "aqua" memuat air minum, produk perawatan, menu warung, dan kemasan.
  Untuk presisi, SELALU gabungkan nama produk + nama produsen:
      cari(produk="aqua", produsen="tirta")   -> 74 produk, semuanya PT Tirta Investama
      cari(produk="wardah", produsen="paragon") -> 1.331 produk kosmetik
  Setiap hasil membawa metadata paginasi (`totalItems`), jadi jumlah total bisa dibaca
  tanpa menelusuri semua halaman.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://bpjph.halal.go.id/cari/sertifikat"
CACHE = Path(__file__).resolve().parent / ".cache_bpjph"
CACHE.mkdir(exist_ok=True)
UA = "HalalCheckPrototype/0.1 (hackathon research; low volume)"
DELAY = 1.5          # detik antar permintaan — jangan dikurangi
_last = [0.0]


def _fetch(params: dict) -> str:
    """GET dengan cache + rate limit. Hanya satu halaman per panggilan."""
    key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    f = CACHE / f"{key}.html"
    if f.exists():
        return f.read_text(encoding="utf-8", errors="ignore")

    gap = time.time() - _last[0]
    if gap < DELAY:
        time.sleep(DELAY - gap)

    url = BASE + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v})
    req = urllib.request.Request(url, headers={"User-Agent": UA})

    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                html = r.read().decode("utf-8", errors="ignore")
            break
        except Exception as e:          # timeout / koneksi putus — ulangi, jangan gagal diam-diam
            last = e
            time.sleep(2 + attempt * 2)
    else:
        raise RuntimeError(f"gagal mengambil {url} setelah 3 percobaan: {last}")
    _last[0] = time.time()
    f.write_text(html, encoding="utf-8")
    return html


def _rsc_text(html: str) -> str:
    """
    Gabungkan seluruh chunk React Server Components yang di-escape sebagai string JS.

    Kenapa begini: payload-nya adalah JSON yang di-embed ke dalam literal string JS,
    jadi tanda kutip di dalam nama produk ter-escape DUA lapis (\\\" bukan \"). Replace
    naif seperti `.replace('\\\\"','"')` akan merusak JSON — itu bug yang membuat
    pencarian "indomie" (8.840 hasil) terbaca kosong.
    """
    parts = []
    for m in re.finditer(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html):
        try:
            parts.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            continue
    return "\n".join(parts)


def _array_after(text: str, key: str = "data") -> tuple[list, dict]:
    """Ambil array JSON setelah `"key":[` dengan pemindai yang sadar-string."""
    marker = f'"{key}":['
    i = text.find(marker)
    if i < 0:
        return [], {}
    start = i + len(marker) - 1
    depth, j, in_str, esc = 0, start, False, False
    while j < len(text):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    break
        j += 1
    try:
        data = json.loads(text[start:j + 1])
    except json.JSONDecodeError:
        return [], {}

    meta = {}
    tail = text[j:j + 400]
    for k in ("currentPage", "totalItems", "pageSize", "totalPages"):
        m = re.search(rf'"{k}":(\d+)', tail)
        if m:
            meta[k] = int(m.group(1))
    return data, meta


def _records(html: str) -> tuple[list[dict], dict]:
    return _array_after(_rsc_text(html), "data")


def _norm(rec: dict) -> dict:
    s = rec.get("sertifikat") or {}
    pu = rec.get("pelaku_usaha") or {}
    pabrik = rec.get("pabrik") or []
    return {
        "nama_produk": rec.get("nama_produk", ""),
        "merek": rec.get("merek_dagang", ""),
        "pelaku_usaha": pu.get("nama_pelaku_usaha", ""),
        "nib": pu.get("nib", ""),
        "no_sertifikat": s.get("no_sertifikat", ""),
        "tgl_terbit": s.get("tgl_terbit_sertifikat", ""),
        "pabrik": pabrik[0].get("alamat", "") if pabrik else "",
        "kab_kota": pabrik[0].get("kab_kota", "") if pabrik else "",
        "provinsi": pabrik[0].get("provinsi", "") if pabrik else "",
        "skala_usaha": rec.get("skala_usaha", ""),
        "jenis_produk": (rec.get("pengajuan") or {}).get("jenis_produk", ""),
        "foto": rec.get("foto", ""),
    }


def cari(produk: str = "", produsen: str = "", no_regis: str = "",
         page: int = 1, max_page: int = 1, jenis: str = "") -> list[dict]:
    """
    Cari sertifikat. `max_page` > 1 untuk menelusuri beberapa halaman.

    `jenis` menyaring kode jenis produk (prefix). Contoh yang teramati:
      A0014 keripik · A0016 kopi/minuman · A0005 kemasan pangan · H0007 tube kemasan
    PENTING: taksonomi ini TIDAK terdokumentasi dan TIDAK konsisten — sebuah entri
    bernama "Kemasan Pangan ..." bisa berkode A0005. Jangan pakai filter ini sebagai
    jaminan kebenaran, hanya untuk mempersempit hasil.
    """
    return cari_full(produk, produsen, no_regis, page, max_page, jenis)[0]


def cari_full(produk: str = "", produsen: str = "", no_regis: str = "",
              page: int = 1, max_page: int = 1, jenis: str = "") -> tuple[list[dict], dict]:
    """Seperti `cari`, tetapi juga mengembalikan metadata paginasi (totalItems dll)."""
    out, seen, meta = [], set(), {}
    for p in range(page, page + max_page):
        params = {"produk": produk, "produsen": produsen, "no_regis": no_regis}
        if p > 1:
            params["page"] = p
        recs, m = _records(_fetch(params))
        if m and not meta:
            meta = m
        if not recs:
            break
        for rec in recs:
            n = _norm(rec)
            if jenis and not n["jenis_produk"].startswith(jenis):
                continue
            k = (n["nama_produk"], n["no_sertifikat"])
            if k not in seen:
                seen.add(k)
                out.append(n)
    return out, meta


# Kode provinsi BPS -> nama. Dipakai untuk menerjemahkan field `provinsi` pada record.
# Catatan: untuk produk luar negeri, field ini berisi NAMA provinsi/negara bagian
# (mis. "Pathum Thani"), bukan kode — jadi harus ditangani sebagai teks apa adanya.
PROVINSI = {
    "11": "Aceh", "12": "Sumatera Utara", "13": "Sumatera Barat", "14": "Riau",
    "15": "Jambi", "16": "Sumatera Selatan", "17": "Bengkulu", "18": "Lampung",
    "19": "Kep. Bangka Belitung", "21": "Kep. Riau", "31": "DKI Jakarta",
    "32": "Jawa Barat", "33": "Jawa Tengah", "34": "DI Yogyakarta", "35": "Jawa Timur",
    "36": "Banten", "51": "Bali", "52": "Nusa Tenggara Barat", "53": "Nusa Tenggara Timur",
    "61": "Kalimantan Barat", "62": "Kalimantan Tengah", "63": "Kalimantan Selatan",
    "64": "Kalimantan Timur", "65": "Kalimantan Utara", "71": "Sulawesi Utara",
    "72": "Sulawesi Tengah", "73": "Sulawesi Selatan", "74": "Sulawesi Tenggara",
    "75": "Gorontalo", "76": "Sulawesi Barat", "81": "Maluku", "82": "Maluku Utara",
    "91": "Papua", "92": "Papua Barat", "93": "Papua Selatan", "94": "Papua Tengah",
    "95": "Papua Pegunungan", "96": "Papua Barat Daya",
}


def provinsi_nama(kode: str) -> str:
    if not kode:
        return "-"
    return PROVINSI.get(kode.strip(), kode)


def asal_produk(r: dict) -> dict:
    """
    Ringkasan asal-usul dari satu record BPJPH.

    Yang BISA dijawab: di mana produk ini diproduksi, oleh siapa, skala usaha,
    lokal atau impor.
    Yang TIDAK BISA dijawab dari data ini: dipasarkan/distribusi ke mana.
    """
    negara = "Indonesia" if provinsi_nama(r["provinsi"]) != r["provinsi"] else "Luar negeri"
    return {
        "pabrik": r["pabrik"] or "-",
        "kab_kota": r["kab_kota"] or "-",
        "provinsi": provinsi_nama(r["provinsi"]),
        "negara": negara,
        "pelaku_usaha": r["pelaku_usaha"],
        "skala_usaha": r["skala_usaha"],
        "no_sertifikat": r["no_sertifikat"],
        "tgl_terbit": r["tgl_terbit"],
        "catatan": "Alamat pabrik menurut sertifikat. Data distribusi TIDAK tersedia.",
    }


# --------------------------------------------------------------------------- CLI
def _ringkas(n: int, meta: dict) -> None:
    if meta.get("totalItems") is not None:
        print(f"\n{n} record diambil · total {meta['totalItems']:,} produk · "
              f"halaman {meta.get('currentPage', 1)}/{meta.get('totalPages', '?')} "
              f"({meta.get('pageSize', '?')}/halaman)".replace(",", "."))
    else:
        print(f"\n{n} record diambil (total tidak terbaca)")


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:
        print("pakai: python bpjph_client.py produk <kata> [halaman]")
        print("       python bpjph_client.py cert <no_sertifikat>")
        print("       python bpjph_client.py produsen <nama>")
        sys.exit(0)

    mode = args[0]
    kw = args[1] if len(args) > 1 else ""
    pages = int(args[2]) if len(args) > 2 else 1
    pages = max(1, min(pages, 5))          # batasi: 10 record/halaman, jangan boros

    if mode == "produk":
        rows, meta = cari_full(produk=kw, max_page=pages,
                               jenis=args[3] if len(args) > 3 else "")
    elif mode == "produsen":
        rows, meta = cari_full(produsen=kw, max_page=pages)
    elif mode == "cert":
        rows, meta = cari_full(no_regis=kw, max_page=pages)
    elif mode == "asal":
        rows, meta = cari_full(produk=kw, max_page=pages)
        for r in rows[:8]:
            a = asal_produk(r)
            print(f"  {r['nama_produk'][:40]}")
            print(f"    {a['pabrik']} · {a['provinsi']} ({a['negara']})")
            print(f"    pelaku: {a['pelaku_usaha']} · skala {a['skala_usaha']} · {a['no_sertifikat']}")
            print()
        _ringkas(len(rows), meta)
        sys.exit(0)
    else:
        print("mode tidak dikenal")
        sys.exit(1)

    for r in rows:
        print(f"  {r['nama_produk'][:38]:40s} {r['no_sertifikat']:20s} {r['tgl_terbit'][:11]}")
        print(f"    merek={r['merek'] or '-'} · pelaku={r['pelaku_usaha'][:28]} · {provinsi_nama(r['provinsi'])}")
    _ringkas(len(rows), meta)
