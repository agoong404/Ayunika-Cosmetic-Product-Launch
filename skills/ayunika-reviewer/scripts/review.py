#!/usr/bin/env python3
"""
Nilai satu draf dengan Reviewer dua lapis — di luar sesi jembatan.

Pemakaian:
    python review.py draf.md AY-SR-101 tiktok
    python review.py draf.md AY-SR-101 tiktok --findings temuan.json
    python review.py draf.md AY-SR-101 tiktok --findings temuan.json --log

Tanpa --findings: hanya lapis-1 (kode).
Dengan --findings: lapis-1 + lapis-2, dan penjaga kutipan menyaring temuan model.
Tanpa --log: tidak menulis entri audit (dipakai untuk pemeriksaan cepat).

Keluaran: JSON {verdict, jumlah_temuan, temuan[], dibuang_llm[], catatan[]}.
Kode keluar: 0 = LOLOS, 1 = TOLAK, 3 = PERLU_DATA (SKU tidak ada di registri), 2 = salah pakai.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "engine" / "reviewer.py").exists() and (p / "agents" / "contract.py").exists():
            return p
    raise SystemExit("Root repo tidak ditemukan")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Reviewer dua lapis untuk satu draf")
    ap.add_argument("draf", help="berkas draf (.md / .txt)")
    ap.add_argument("sku")
    ap.add_argument("platform", choices=("tiktok", "instagram", "marketplace"))
    ap.add_argument("--findings", help="JSON temuan lapis-2: {\"findings\": [...]}")
    ap.add_argument("--log", action="store_true", help="tulis entri ke audit log")
    ap.add_argument("--iterasi", type=int, default=1)
    a = ap.parse_args(argv[1:])

    draf_path = Path(a.draf)
    if not draf_path.exists():
        print(f"Draf tidak ada: {draf_path}")
        return 2
    teks = draf_path.read_text(encoding="utf-8").strip()
    if not teks:
        print("Draf kosong — tidak ada yang bisa dinilai.")
        return 2

    findings = None
    if a.findings:
        try:
            data = json.loads(Path(a.findings).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"JSON temuan tidak sah: {e}")
            return 2
        findings = data.get("findings") if isinstance(data, dict) else data
        if not isinstance(findings, list):
            print("Temuan harus berupa daftar: {\"findings\": [ ... ]}")
            return 2

    root = repo_root()
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "engine"))
    from reviewer import Reviewer  # noqa: E402

    R = Reviewer()
    hasil = R.review(teks, a.sku, a.platform, a.iterasi,
                     llm_findings=findings, log=a.log)

    keluaran = {
        "sku": a.sku,
        "platform": a.platform,
        "iterasi": a.iterasi,
        "lapis2": bool(findings),
        "verdict": hasil.verdict,
        "jumlah_temuan": len(hasil.violations),
        "temuan": [v.as_dict() for v in hasil.violations],
        "dibuang_llm": hasil.dropped_llm,
        "catatan": hasil.catatan,
    }
    print(json.dumps(keluaran, ensure_ascii=False, indent=2))
    if hasil.verdict == "LOLOS":
        return 0
    if hasil.verdict == "PERLU_DATA":
        # Bukan lulus: data produk tidak ada, jadi tidak semua aturan bisa dinilai.
        return 3
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv))
