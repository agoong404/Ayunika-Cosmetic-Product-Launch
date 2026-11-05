"""
validate_asset.py — proofreader untuk kartu produk.

Yang diperiksa adalah PROOF (PNG hasil render), bukan file desainnya. OCR membaca
gambar, lalu tiga sinyal independen memutuskan:

  1. geometri + luber (deterministik, dari sidecar render)
  2. deret angka (harga, isi, BPOM) — tahan terhadap OCR yang membaca "Rpl49.000"
  3. recall kata (fuzzy) + gerbang kualitas OCR

Silang terakhir: teks hasil OCR dinilai Reviewer (R-01..R-21), karena teks yang
terbaca benar belum tentu klaim yang sah.

Pemakaian:
    python engine/validate_asset.py --semua
    python engine/validate_asset.py submission_templates/cards/C-17-kartu.png
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "engine"))

from asset_builder import muat_manifest, render  # noqa: E402

TESSDATA = BASE / "engine" / "tessdata"
STOPWORDS = {"yang", "pada", "untuk", "dengan", "dari", "ini", "itu", "atau", "dan"}
AMBANG_KATA = 0.86
AMBANG_RECALL_BLOK = 0.90
AMBANG_RECALL_GLOBAL = 0.95
AMBANG_CONF = 60.0


# ------------------------------------------------------------------ dataclass
@dataclass
class Temuan:
    kunci: str
    jenis: str
    pesan: str


@dataclass
class Hasil:
    ok: bool
    status: str
    temuan: list[Temuan] = field(default_factory=list)
    teks_ocr: str = ""
    ringkas: str = ""
    detik: float = 0.0

    def laporan(self) -> str:
        baris = [f"{self.status} · {self.ringkas}"]
        for t in self.temuan:
            baris.append(f"  × [{t.jenis}] {t.pesan}")
        return "\n".join(baris)


# ------------------------------------------------------------------ tesseract
def _tesseract() -> Path | None:
    kandidat = [
        os.environ.get("TESSERACT_CMD", ""),
        shutil.which("tesseract") or "",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / "tesseract.exe"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    ]
    for k in kandidat:
        if k and Path(k).exists():
            return Path(k)
    return None


def _bahasa(tess: Path) -> str:
    cmd = [str(tess), "--list-langs"]
    if TESSDATA.exists():
        cmd += ["--tessdata-dir", str(TESSDATA)]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    daftar = {b.strip() for b in p.stdout.splitlines()[1:] if b.strip()}
    return "ind+eng" if "ind" in daftar else "eng"


def ocr_tersedia() -> tuple[bool, str]:
    tess = _tesseract()
    if tess is None:
        return False, ("Tesseract tidak ditemukan. Pasang: "
                       "winget install --id UB-Mannheim.TesseractOCR -e")
    p = subprocess.run([str(tess), "--version"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    versi = (p.stdout or p.stderr).splitlines()[0] if (p.stdout or p.stderr) else "?"
    return True, f"{versi} · bahasa {_bahasa(tess)}"


# ------------------------------------------------------------------ baca
def normalisasi(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s: str) -> list[str]:
    kata = re.findall(r"[a-z]{4,}", normalisasi(s))
    return [k for k in kata if k not in STOPWORDS]


def baca(png: Path, psm: int = 11) -> tuple[str, list[dict], float]:
    tess = _tesseract()
    if tess is None:
        raise RuntimeError("Tesseract tidak tersedia")
    cmd = [str(tess), str(png), "stdout", "-l", _bahasa(tess), "--psm", str(psm), "tsv"]
    if TESSDATA.exists():
        cmd += ["--tessdata-dir", str(TESSDATA)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"tesseract gagal: {(p.stderr or '')[:200]}")

    rows = list(csv.DictReader(io.StringIO(p.stdout), delimiter="\t"))
    kata = [r for r in rows if (r.get("level") or "") == "5" and (r.get("text") or "").strip()]
    baris: dict[tuple, list[str]] = {}
    for r in kata:
        k = (r.get("block_num"), r.get("par_num"), r.get("line_num"))
        baris.setdefault(k, []).append(r["text"])
    teks = "\n".join(" ".join(v) for v in baris.values())

    conf = [float(r["conf"]) for r in kata if r.get("conf") not in (None, "", "-1")]
    rerata = sum(conf) / len(conf) if conf else 0.0
    return teks, kata, rerata


def _dimensi_png(png: Path) -> tuple[int, int]:
    b = png.read_bytes()[:24]
    return struct.unpack(">II", b[16:24])


def _runs_angka(s: str) -> list[str]:
    return [re.sub(r"\D", "", m) for m in re.findall(r"\d[\d.,]*", s)]


# ------------------------------------------------------------------ banding
def banding(manifest: dict, teks: str, kata: list[dict], sidecar: dict,
            conf: float, mulai: float | None = None) -> Hasil:
    mulai = mulai if mulai is not None else time.perf_counter()
    temuan: list[Temuan] = []

    # 1. geometri + luber (deterministik)
    W, H = manifest["ukuran"]
    if sidecar.get("ukuran") != [W, H]:
        temuan.append(Temuan("ukuran", "geometri",
                             f"gambar {sidecar.get('ukuran')} ≠ {[W, H]}"))
    for k, b in (sidecar.get("blok") or {}).items():
        if b.get("meluber"):
            temuan.append(Temuan(k, "terpotong",
                                 f"blok '{k}' butuh {b['butuh_h']}px, tersedia {b['h']}px"))
    for w in kata:
        try:
            l, t, ww, hh = (int(w["left"]), int(w["top"]), int(w["width"]), int(w["height"]))
        except (KeyError, ValueError):
            continue
        if l <= 2 or t <= 2 or l + ww >= W - 2 or t + hh >= H - 2:
            temuan.append(Temuan(w.get("text", "?"), "terpotong",
                                 f"kata '{w.get('text')}' menyentuh tepi gambar"))
            break

    # 2. deret angka (keras)
    exp: set[str] = set()
    for b in manifest["blok"]:
        if b.get("jenis") in ("harga", "isi", "bpom", "angka"):
            for r in _runs_angka(b["teks"]):
                if len(r) >= 2:
                    exp.add(r)
    ocr_runs = _runs_angka(teks)
    ocr_gabung = "".join(ocr_runs)
    for r in sorted(exp):
        if r not in ocr_gabung:
            temuan.append(Temuan(r, "angka",
                                 f"angka {r} tidak terbaca di gambar (lembar produk memuatnya)"))
    for r in ocr_runs:
        if len(r) >= 5 and r not in exp and not any(r in e or e in r for e in exp):
            temuan.append(Temuan(r, "angka", f"angka {r} tidak ada di lembar produk"))

    # 3. recall kata (lunak) + gerbang kualitas
    ocr_tok = _tokens(teks)
    total, cocok = 0, 0
    for b in manifest["blok"]:
        tok = _tokens(b["teks"])
        if not tok:
            continue
        hit = 0
        for t in tok:
            if any(SequenceMatcher(None, t, o).ratio() >= AMBANG_KATA for o in ocr_tok):
                hit += 1
        total += len(tok)
        cocok += hit
        if hit / len(tok) < AMBANG_RECALL_BLOK:
            hilang = [t for t in tok
                      if not any(SequenceMatcher(None, t, o).ratio() >= AMBANG_KATA
                                 for o in ocr_tok)]
            temuan.append(Temuan(b["kunci"], "teks",
                                 f"blok '{b['kunci']}' hanya {hit}/{len(tok)} kata dikenali "
                                 f"— hilang: {', '.join(hilang[:4])}"))
    recall = (cocok / total) if total else 0.0
    if recall < AMBANG_RECALL_GLOBAL and not any(t.jenis == "teks" for t in temuan):
        temuan.append(Temuan("global", "teks", f"recall kata {recall:.0%} < 95%"))

    # 4. silang Reviewer
    from reviewer import Reviewer
    rev = Reviewer().review(teks, manifest.get("sku", "AY-SR-101"), "instagram", 1, log=False)

    # putusan
    # Catatan penting: recall rendah dengan keyakinan TINGGI berarti gambar memang
    # berbeda dari naskah → TOLAK. Recall rendah dengan keyakinan RENDAH berarti
    # OCR-nya yang buruk → PERLU_TINJAU, jangan menuduh.
    keras = [t for t in temuan if t.jenis in ("geometri", "terpotong", "angka")]
    if keras:
        status = "TOLAK"
    elif conf < AMBANG_CONF:
        status = "PERLU_TINJAU"
    elif temuan or rev.violations:
        status = "TOLAK"
    else:
        status = "LULUS"
    for v in rev.violations:
        temuan.append(Temuan(v.rule_id, "kepatuhan", f"{v.rule_id}: {v.reason}"))
    if rev.violations and status == "LULUS":
        status = "TOLAK"

    detik = time.perf_counter() - mulai
    ringkas = (f"OCR {conf:.0f}% · recall {recall:.0%} · {len(temuan)} temuan · "
               f"{detik:.2f}s")
    return Hasil(ok=status == "LULUS", status=status, temuan=temuan,
                 teks_ocr=teks, ringkas=ringkas, detik=detik)


def validasi_png(png: Path, manifest: dict, sidecar: dict) -> Hasil:
    t0 = time.perf_counter()
    teks, kata, conf = baca(png)
    return banding(manifest, teks, kata, sidecar, conf, mulai=t0)


def validasi(manifest: dict, *, ubah: dict | None = None,
             potong: dict | None = None) -> Hasil:
    out = Path(tempfile.gettempdir()) / "halal_c17" / "uji.png"
    sc = render(manifest, out, ubah=ubah, potong=potong)
    return validasi_png(out, manifest, sc)


# ------------------------------------------------------------------ CLI
SKENARIO = [
    ("bersih", {}, {}, "LULUS"),
    ("harga_salah", {"harga": "Rp139.000"}, {}, "TOLAK"),
    ("terpotong", {}, {"aktif": {"lebar_px": 300}}, "TOLAK"),
    ("klaim_terlarang", {"peringatan": "Formula ini memutihkan kulit."}, {}, "TOLAK"),
]


def main(argv: list[str]) -> int:
    ada, info = ocr_tersedia()
    print(f"OCR: {info}")
    if not ada:
        return 2

    if "--semua" in argv:
        m = muat_manifest()
        gagal = 0
        for nama, ubah, potong, harap in SKENARIO:
            h = validasi(m, ubah=ubah, potong=potong)
            tanda = "OK" if h.status == harap else "SALAH"
            print(f"\n[{nama}] harap {harap} → {h.status} ({tanda})")
            print(h.laporan())
            if h.status != harap:
                gagal += 1
        print(f"\n{len(SKENARIO) - gagal}/{len(SKENARIO)} skenario sesuai harapan")
        return 0 if gagal == 0 else 1

    if len(argv) >= 1 and argv[0].endswith(".png"):
        png = Path(argv[0])
        m = muat_manifest()
        sc = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
        h = validasi_png(png, m, sc)
        print(h.laporan())
        return 0 if h.ok else 1

    print(__doc__)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
