#!/usr/bin/env python3
"""
Periksa rencana sebelum Writer menulis.

Pemakaian:
    python check_plan.py agents/.wb/jawaban-plan.json

Yang dicetak hanya yang boleh diketahui Writer: struktur, fakta yang boleh,
fakta yang dilarang, harga, dan batas platform. Rulebook TIDAK dicetak —
Writer bukan pengawas kepatuhannya sendiri, dan itu keputusan desain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "engine" / "reviewer.py").exists() and (p / "agents" / "contract.py").exists():
            return p
    raise SystemExit("Root repo tidak ditemukan")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    berkas = Path(argv[1])
    if not berkas.exists():
        print(f"Rencana tidak ada: {berkas}")
        print("Jalankan skill `lolos-planner` lebih dulu.")
        return 2

    root = repo_root()
    sys.path.insert(0, str(root))
    from agents.contract import BATAS, ContractError, validate_plan  # noqa: E402

    try:
        data = json.loads(berkas.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"JSON tidak sah: {e}")
        return 1

    try:
        plan = validate_plan(data)
    except ContractError as e:
        print("RENCANA DITOLAK KONTRAK")
        for m in e.masalah:
            print(f"  - {m}")
        return 1

    batas = BATAS[plan.platform]
    print(f"RENCANA SAH — {plan.sku} · {plan.platform}")
    print(f"\nSudut   : {plan.angle}")
    print(f"Struktur: {' → '.join(plan.struktur)}")
    print(f"Harga   : {plan.harga}"
          + (f" · promo {plan.harga_promo}" if plan.harga_promo else ""))
    print(f"BPOM    : {plan.bpom or '(tidak ada)'}")
    print(f"Isi     : {plan.isi or '(tidak ada)'}")

    print("\nFakta yang BOLEH dipakai (jangan menambah di luar ini):")
    for f in plan.fakta_boleh:
        print(f"  + {f}")

    print("\nFakta yang DILARANG:")
    for f in plan.fakta_dilarang:
        print(f"  - {f}")

    print(f"\nBatas platform: maks {batas['kata_maks']} kata · "
          f"{batas['karakter_maks']} karakter · {batas['emoji_maks']} emoji")
    print(f"Disclaimer wajib: {plan.disclaimer}")
    if plan.catatan:
        print(f"Catatan Planner: {plan.catatan}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv))
