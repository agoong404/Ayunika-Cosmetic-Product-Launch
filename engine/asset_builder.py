"""
asset_builder.py — render kartu produk (1080x1350) dari manifest teks.

Ini "file desain" dalam analogi percetakan: yang dibuat di sini BELUM tentu benar.
Yang menentukan adalah proof-nya (PNG) yang dibaca `validate_asset.py` lewat OCR.

Pemakaian:
    python engine/asset_builder.py --tulis     # ke submission_templates/cards/
    python engine/asset_builder.py             # ke folder sementara
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MANIFEST = BASE / "dataset_c" / "assets" / "C-17_kartu_produk.json"
CHROME = Path(os.environ.get("CHROME_PATH",
                             r"C:\Program Files\Google\Chrome\Application\chrome.exe"))


# ------------------------------------------------------------------ teks
def pas_font(teks: str, lebar: int, tinggi: int, maks: int = 100,
             tinggi_baris: float = 1.2) -> tuple[int, str, int]:
    """Cari font terbesar yang membuat teks muat; kembalikan (fs, teks_wrap, butuh_h)."""
    for fs in range(maks, 9, -1):
        kolom = max(8, int(lebar / (fs * 0.60)))
        baris = []
        for b in str(teks).split("\n"):
            baris.extend(textwrap.wrap(b, kolom) or [""])
        butuh = int(len(baris) * fs * tinggi_baris)
        if butuh <= tinggi:
            return fs, "\n".join(baris), butuh
    kolom = max(8, int(lebar / (10 * 0.60)))
    baris = []
    for b in str(teks).split("\n"):
        baris.extend(textwrap.wrap(b, kolom) or [""])
    return 10, "\n".join(baris), int(len(baris) * 10 * tinggi_baris)


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ------------------------------------------------------------------ manifest
def muat_manifest(path: Path | None = None) -> dict:
    return json.loads((path or MANIFEST).read_text(encoding="utf-8"))


def _efektif(manifest: dict, ubah: dict | None, potong: dict | None) -> dict:
    """Terapkan override teks/ukuran tanpa mengubah manifest asli."""
    blok = []
    for b in manifest["blok"]:
        c = dict(b)
        if ubah and c["kunci"] in ubah:
            c["teks"] = ubah[c["kunci"]]
        if potong and c["kunci"] in potong:
            ub = potong[c["kunci"]]
            x, y, w, h = c["kotak"]
            c["kotak"] = [x, y, ub.get("lebar_px", w), ub.get("tinggi_px", h)]
            # Blok yang sengaja dipersempit TIDAK boleh mengecilkan font sendiri —
            # kalau tidak, ia akan "menyesuaikan diri" dan tidak pernah terpotong.
            c["_paksa"] = True
        blok.append(c)
    return {"id": manifest.get("id"), "sku": manifest.get("sku"),
            "ukuran": manifest["ukuran"], "blok": blok}


# ------------------------------------------------------------------ render
def _html(blok: list[dict], ukuran: tuple[int, int]) -> str:
    W, H = ukuran
    bagian = []
    for b in blok:
        x, y, w, h = b["kotak"]
        if b.get("_paksa"):
            fs = b.get("font", 40)
            kolom = max(8, int(w / (fs * 0.60)))
            baris = []
            for t in str(b["teks"]).split("\n"):
                baris.extend(textwrap.wrap(t, kolom) or [""])
            isi = "\n".join(baris)
            butuh = int(len(baris) * fs * 1.2)
        else:
            fs, isi, butuh = pas_font(b["teks"], w, h, b.get("font", 40))
        b["_fs"], b["_isi"], b["_butuh"] = fs, isi, butuh
        fam = ("'Cascadia Mono',Consolas,monospace" if b.get("mono")
               else "'Segoe UI',system-ui,sans-serif")
        bagian.append(
            f'<div class="blok" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
            f'font-size:{fs}px;font-weight:{b.get("tebal", 400)};font-family:{fam}">'
            f'{esc(isi)}</div>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#ffffff;
  font-family:'Segoe UI',system-ui,sans-serif;color:#0f172a}}
.aksen{{position:absolute;left:0;top:0;width:{W}px;height:14px;background:#4338ca}}
.panel{{position:absolute;left:60px;top:450px;width:960px;height:170px;
  background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px}}
.garis{{position:absolute;left:80px;top:430px;width:920px;height:1px;background:#e2e8f0}}
.blok{{position:absolute;overflow:hidden;white-space:pre-wrap;line-height:1.2}}
</style></head><body>
<div class="aksen"></div><div class="panel"></div><div class="garis"></div>
{"".join(bagian)}
</body></html>"""


def render(manifest: dict, keluar: Path, *, ubah: dict | None = None,
           potong: dict | None = None, skala: int = 1) -> dict:
    """Render kartu ke PNG. Mengembalikan sidecar (bbox, fs, butuh_h, meluber)."""
    eff = _efektif(manifest, ubah, potong)
    W, H = eff["ukuran"]
    html = _html(eff["blok"], (W, H))

    keluar = Path(keluar)
    keluar.parent.mkdir(parents=True, exist_ok=True)
    tmp = keluar.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    try:
        subprocess.run([
            str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--no-sandbox", f"--screenshot={keluar.resolve()}",
            f"--window-size={W},{H}", f"--force-device-scale-factor={skala}",
            tmp.resolve().as_uri(),
        ], check=True, capture_output=True)
    finally:
        tmp.unlink(missing_ok=True)

    blok = {}
    for b in eff["blok"]:
        x, y, w, h = b["kotak"]
        blok[b["kunci"]] = {"x": x, "y": y, "w": w, "h": h,
                            "fs": b["_fs"], "butuh_h": b["_butuh"],
                            "meluber": b["_butuh"] > h + 0.5,
                            "teks": b["teks"], "jenis": b.get("jenis", "kata")}

    sidik = hashlib.sha1(json.dumps(eff, sort_keys=True, ensure_ascii=False)
                         .encode("utf-8")).hexdigest()[:12]
    return {"ukuran": [W, H], "skala": skala, "sha1": sidik,
            "blok": blok, "manifest": eff}


def main(argv: list[str]) -> int:
    if "--tulis" in argv:
        keluar = BASE / "submission_templates" / "cards" / "C-17-kartu.png"
    else:
        keluar = Path(tempfile.gettempdir()) / "halal_c17" / "C-17-kartu.png"

    m = muat_manifest()
    sc = render(m, keluar)
    (keluar.with_suffix(".json")).write_text(
        json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")

    ukuran = keluar.stat().st_size / 1024
    print(f"kartu : {keluar} ({ukuran:.0f} KB, {sc['ukuran'][0]}x{sc['ukuran'][1]})")
    print(f"sidik : {sc['sha1']}")
    luber = [k for k, v in sc["blok"].items() if v["meluber"]]
    print(f"blok  : {len(sc['blok'])} · meluber: {luber or 'tidak ada'}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
