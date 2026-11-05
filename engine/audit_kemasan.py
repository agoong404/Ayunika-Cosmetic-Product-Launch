"""
audit_kemasan.py — layer reviewer AWAL: periksa kemasan & komposisi sebelum konten ditulis.

Kenapa dipisah dari review():

  review() menilai DRAF KONTEN (apakah kalimatnya melanggar aturan).
  audit_kemasan() menilai PRODUK (apakah labelnya lengkap, izinnya berlaku,
  komposisinya dalam batas). Menjalankan ini lebih dulu mencegah satu kelas
  masalah yang tidak bisa diperbaiki Writer: konten yang benar di atas produk
  yang izinnya kedaluwarsa.

Pemakaian:
    python audit_kemasan.py AY-SR-101
    python audit_kemasan.py --semua
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "engine"))

from reviewer import Reviewer  # noqa: E402


def _bagian_label(sheet: str) -> str:
    """Ambil hanya blok 'Tulisan di kemasan' — bukan seluruh lembar produk."""
    tanda = "## Tulisan di kemasan"
    i = sheet.find(tanda)
    if i < 0:
        return ""
    sisa = sheet[i + len(tanda):]
    j = sisa.find("\n## ")
    return sisa if j < 0 else sisa[:j]


def audit(reviewer: Reviewer, sku: str) -> list[dict]:
    masalah: list[dict] = []
    sheet = reviewer.sheet_by_sku.get(sku, "")
    label = _bagian_label(sheet)

    # ---- R-16 izin edar / notifikasi ----
    izin = reviewer.izin_edar.get(sku)
    if izin is None:
        masalah.append({"rule_id": "R-16", "masalah": "tidak ada notifikasi/izin edar di registri"})
    elif not reviewer._berlaku(izin):
        masalah.append({"rule_id": "R-16",
                        "masalah": f"notifikasi {izin.get('nomor')} {izin.get('status')} "
                                   f"(s/d {izin.get('berlaku_sampai')})"})

    # ---- R-17 izin produksi kategori ----
    kategori = (reviewer.products[sku].get("kategori") or "").strip().lower()
    prod = reviewer.izin_produksi.get(kategori)
    if prod is None:
        masalah.append({"rule_id": "R-17", "masalah": f"tidak ada izin produksi untuk '{kategori}'"})
    elif not reviewer._berlaku(prod):
        masalah.append({"rule_id": "R-17",
                        "masalah": f"izin produksi '{kategori}' {prod.get('status')} "
                                   f"(s/d {prod.get('berlaku_sampai')})"})

    # ---- kelengkapan label ----
    if not label.strip():
        masalah.append({"rule_id": "R-02", "masalah": "lembar produk tidak memuat tulisan kemasan"})
    else:
        if izin and izin.get("nomor") and izin["nomor"] not in label:
            masalah.append({"rule_id": "R-02",
                            "masalah": f"nomor {izin['nomor']} tidak tercetak di kemasan"})
        if "Komposisi:" not in label:
            masalah.append({"rule_id": "R-02", "masalah": "komposisi tidak tercetak di kemasan"})
        if "Peringatan:" not in label:
            masalah.append({"rule_id": "R-02", "masalah": "peringatan tidak tercetak di kemasan"})

        # ---- R-03 nomor sertifikat halal kedaluwarsa yang masih tercetak ----
        for cert in reviewer.certs.values():
            nomor = cert.get("nomor", "")
            if not nomor or nomor not in label:
                continue
            if not reviewer._berlaku(cert):
                masalah.append({"rule_id": "R-03",
                                "masalah": f"nomor halal {nomor} masih tercetak, "
                                           f"padahal {cert.get('status')} "
                                           f"(s/d {cert.get('berlaku_sampai')})"})

    # ---- R-21 komposisi vs batas pengawet ----
    for m in reviewer.audit_komposisi(sku):
        masalah.append({"rule_id": m["rule_id"], "masalah": m["alasan"]})

    return masalah


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    reviewer = Reviewer()
    if argv[0] == "--semua":
        daftar = list(reviewer.products)
    else:
        daftar = argv
        for sku in daftar:
            if sku not in reviewer.products:
                print(f"SKU tidak dikenal: {sku}")
                return 2

    total = 0
    for sku in daftar:
        masalah = audit(reviewer, sku)
        status = "BERSIH" if not masalah else f"{len(masalah)} masalah"
        print(f"\n{sku} · {reviewer.products[sku]['nama_produk']} — {status}")
        for m in masalah:
            print(f"  ✗ {m['rule_id']}  {m['masalah']}")
        total += len(masalah)

    print(f"\nTotal masalah kemasan: {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
