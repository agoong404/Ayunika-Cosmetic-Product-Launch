#!/usr/bin/env python3
"""
Muat bundel konteks Planner untuk satu SKU + platform.

Pemakaian:
    python load_context.py AY-SR-101 tiktok

Yang dicetak: ringkasan produk dari registri, status sertifikat, lembar produk
(satu-satunya sumber fakta), brief, spesifikasi platform, dan nada merek.
Rulebook sengaja TIDAK dimuat — Planner tidak perlu membaca aturan; ia hanya
menyusun kerangka dari fakta yang boleh dipakai.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def repo_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "engine" / "reviewer.py").exists() and (p / "agents" / "contract.py").exists():
            return p
    raise SystemExit("Root repo tidak ditemukan (cari engine/reviewer.py + agents/contract.py)")


def baca(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def rupiah(nilai: str) -> str:
    """149000 -> Rp149.000 (CSV menyimpan angka mentah)."""
    try:
        return "Rp{:,}".format(int(str(nilai).strip())).replace(",", ".")
    except (TypeError, ValueError):
        return nilai or "(tidak ada)"


def bagian(judul: str, isi: str) -> None:
    print(f"\n## {judul}\n")
    print(isi if isi.strip() else "(kosong)")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    sku, platform = argv[1], argv[2]
    root = repo_root()
    data = root / "dataset_c"

    sys.path.insert(0, str(root))
    from agents.contract import BATAS, PLATFORMS  # noqa: E402

    if platform not in PLATFORMS:
        print(f"platform '{platform}' tidak dikenal. Pilihan: {', '.join(PLATFORMS)}")
        return 1

    produk = list(csv.DictReader(open(data / "products.csv", encoding="utf-8")))
    baris = next((r for r in produk if r["sku"] == sku), None)
    if baris is None:
        print(f"SKU '{sku}' tidak dikenal. Pilihan: {', '.join(r['sku'] for r in produk)}")
        return 1

    print(f"# Bundel Planner — {sku} · {platform}")

    ringkas = "\n".join([
        f"- Nama produk : {baris['nama_produk']}",
        f"- Kategori    : {baris['kategori']}",
        f"- Isi bersih  : {baris['isi']}",
        f"- Harga normal: {rupiah(baris['harga'])}",
        f"- Harga promo : {rupiah(baris['harga_promo']) if baris['harga_promo'] else '(tidak ada)'}",
        f"- Kuota promo : {baris['kuota_promo'] or '(tidak ada)'}",
        f"- Notifikasi  : {baris['notifikasi_bpom']}",
        f"- Status halal: {baris['cert_status']}",
    ])
    bagian("Registri produk (products.csv)", ringkas)

    sert = list(csv.DictReader(open(data / "certificates.csv", encoding="utf-8")))
    milik = [s for s in sert if sku in (s.get("sku_tercakup") or "").split("|")]
    if milik:
        isi = "\n".join(
            f"- {s['cert_id']} · nomor {s['nomor']} · status {s['status']} "
            f"(berlaku sampai {s['berlaku_sampai']})" for s in milik)
    else:
        isi = ("Tidak ada sertifikat atas nama SKU ini. **Jangan** menaruh klaim halal "
               "di fakta_boleh.")
    bagian("Registri sertifikat (certificates.csv)", isi)

    nomor = sku.split("-")[-1]
    lembar = sorted((data / "product_sheets").glob(f"PS-{nomor}_*.md"))
    bagian("Lembar produk — SATU-SATUNYA sumber fakta",
           baca(lembar[0]) if lembar else "(lembar produk tidak ditemukan)")

    briefs = sorted((data / "briefs").glob("*.md"))
    pilih = next((b for b in briefs if baris["nama_produk"].split()[-1].lower()
                  in b.name.lower()), briefs[0] if briefs else None)
    bagian("Brief kampanye", baca(pilih) if pilih else "(brief tidak ditemukan)")

    bagian("Spesifikasi platform", baca(data / "platform_specs.md"))
    bagian("Nada merek", baca(data / "brand_tone_guide.md"))

    batas = BATAS[platform]
    print(f"\n## Batas keras platform {platform}\n")
    print(f"- maks {batas['kata_maks']} kata · maks {batas['karakter_maks']} karakter "
          f"· maks {batas['emoji_maks']} emoji")

    print("\n## Langkah berikutnya\n")
    print("Susun rencana JSON, lalu:")
    print("  python -m agents.workbuddy save plan agents/.wb/jawaban-plan.json")
    print("Setelah tersimpan, lanjut ke skill `ayunika-writer`.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv))
