"""
harness.py — menjalankan loop 40 kali dan memeriksa apakah ada yang rusak di tengah jalan.

Yang diuji bukan "apakah kontennya bagus" — itu tugas Reviewer dan manusia. Yang
diuji di sini adalah **mesinnya**:

  · apakah loop selalu berhenti (tidak berputar tanpa akhir)
  · apakah cabang eskalasi benar-benar tercapai
  · apakah agent yang melempar exception ditangani, bukan menjatuhkan proses
  · apakah ada konten yang terbit tanpa melewati persetujuan
  · apakah rantai audit tetap utuh setelah 40 kali jalan

Empat skenario, sengaja dibuat berbeda supaya semua cabang terlewati:

  normal     Planner + Writer bawaan. Harusnya terbit di iterasi 1.
  scripted   Draf manusia v1 → v2 → v3 (14 → 4 → 0 temuan). Menguji siklus penuh.
  stubborn   Writer yang tidak pernah memperbaiki. Harus eskalasi, bukan terbit.
  crash      Writer gagal di iterasi 2. Harus GAGAL, bukan exception mentah.

Jalankan:
    python -m agents.harness                 # 40 run
    python -m agents.harness --agents team   # pakai agent rekan tim
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

# Log uji dipisah supaya tidak mengotori audit log sesi manual.
AUDIT_DIR = Path(os.environ.get("HARNESS_AUDIT_DIR")
                 or Path(tempfile.gettempdir()) / "halal_harness_audit")
os.environ["HALAL_AUDIT_DIR"] = str(AUDIT_DIR)

from agents.registry import load_agents            # noqa: E402
from governance import ApprovalGate, AuditLog      # noqa: E402
from pipeline import ContentPipeline               # noqa: E402
from reviewer import Reviewer                      # noqa: E402

SKUS = ["AY-SR-101", "AY-BL-102", "AY-FW-103", "AY-SC-104"]
PLATFORMS = ["tiktok", "instagram", "marketplace"]
BRIEF = (ROOT / "dataset_c" / "briefs" / "BRF-101_launch_bright_serum.md").read_text(encoding="utf-8")


@dataclass
class Run:
    no: int
    skenario: str
    sku: str
    platform: str
    harapan: str
    status: str = ""
    iterasi: int = 0
    temuan: list[int] = field(default_factory=list)
    plan_id: str = ""
    error: str = ""
    masalah: list[str] = field(default_factory=list)
    detik: float = 0.0

    @property
    def lolos(self) -> bool:
        return not self.masalah


def susun_rencana(agen: str) -> list[dict]:
    """Matriks 40 run. Sengaja eksplisit, bukan dirandom — supaya bisa diulang."""
    rencana: list[dict] = []
    for sku in SKUS:
        for plat in PLATFORMS:
            rencana.append({"skenario": "normal", "sku": sku, "platform": plat,
                            "harapan": "TERBIT", "agents": agen})
    for sku in SKUS:
        for plat in PLATFORMS:
            rencana.append({"skenario": "stubborn", "sku": sku, "platform": plat,
                            "harapan": "ESKALASI", "agents": "stubborn"})
    for sku in SKUS:
        for plat in PLATFORMS:
            rencana.append({"skenario": "crash", "sku": sku, "platform": plat,
                            "harapan": "GAGAL", "agents": "crash"})
    for plat in PLATFORMS:
        rencana.append({"skenario": "scripted", "sku": "AY-SR-101", "platform": plat,
                        "harapan": "TERBIT", "agents": "scripted"})
    # Satu ulangan identik: memastikan hasil tidak berubah antar-jalan.
    rencana.append({"skenario": "scripted", "sku": "AY-SR-101", "platform": "tiktok",
                    "harapan": "TERBIT", "agents": "scripted", "ulang": True})
    return rencana


def periksa(r: Run, hasil) -> None:
    """Invarian yang harus selalu benar, apa pun skenarionya."""
    if r.status != r.harapan:
        r.masalah.append(f"status {r.status} != harapan {r.harapan}")
    if r.iterasi > ContentPipeline.MAX_ITERASI:
        r.masalah.append(f"iterasi {r.iterasi} melewati batas {ContentPipeline.MAX_ITERASI}")
    # Saat GAGAL di tengah iterasi, review terakhir belum sempat terjadi.
    if r.status != "GAGAL" and len(hasil.riwayat) != r.iterasi:
        r.masalah.append(f"riwayat {len(hasil.riwayat)} != iterasi {r.iterasi}")
    if len(hasil.riwayat) > r.iterasi:
        r.masalah.append(f"riwayat {len(hasil.riwayat)} melebihi iterasi {r.iterasi}")

    if r.status == "TERBIT":
        if not r.plan_id:
            r.masalah.append("TERBIT tanpa plan approval")
        if not hasil.konten_final.strip():
            r.masalah.append("TERBIT dengan konten kosong")
        if not hasil.riwayat or hasil.riwayat[-1]["verdict"] != "LOLOS":
            r.masalah.append("TERBIT padahal review terakhir bukan LOLOS")
    else:
        if hasil.konten_final.strip():
            r.masalah.append(f"{r.status} tetapi masih menyimpan konten final")
        if r.plan_id:
            r.masalah.append(f"{r.status} tetapi tetap membuat plan publikasi")

    if r.status == "ESKALASI" and r.iterasi < ContentPipeline.MAX_ITERASI:
        r.masalah.append("ESKALASI sebelum mencapai batas iterasi")


def jalankan(satu: dict, no: int, log: AuditLog) -> Run:
    r = Run(no=no, skenario=satu["skenario"], sku=satu["sku"],
            platform=satu["platform"], harapan=satu["harapan"])
    mulai = time.perf_counter()
    try:
        planner, writer = load_agents(satu["agents"], kind_platform=satu["platform"])
        pipe = ContentPipeline(reviewer=Reviewer(audit=log), log=log,
                               gate=ApprovalGate(log))
        hasil = pipe.run(BRIEF, satu["sku"], satu["platform"],
                         planner=planner, writer=writer)
        r.status, r.iterasi = hasil.status, hasil.iterasi
        r.temuan = [h["jumlah_temuan"] for h in hasil.riwayat]
        r.plan_id, r.error = hasil.plan_id, hasil.error
        periksa(r, hasil)
    except Exception as e:                          # noqa: BLE001
        # Exception yang lolos ke sini berarti orkestrator gagal menangkapnya.
        r.status = "EXCEPTION"
        r.error = f"{type(e).__name__}: {e}"
        r.masalah.append("exception lolos dari orkestrator")
        r.masalah.append(traceback.format_exc(limit=3).splitlines()[-1])
    r.detik = time.perf_counter() - mulai
    return r


def main(argv: list[str]) -> int:
    agen = "mine"
    for i, a in enumerate(argv):
        if a == "--agents" and i + 1 < len(argv):
            agen = argv[i + 1]

    if AUDIT_DIR.exists():
        for f in AUDIT_DIR.glob("*.jsonl"):
            f.unlink()
    log = AuditLog()
    rencana = susun_rencana(agen)

    print(f"Harness Challenge C · {len(rencana)} run · agent: {agen}")
    print(f"audit terpisah: {log.path}")
    print("=" * 96)
    print(f"{'#':>3} {'skenario':9s} {'sku':11s} {'platform':12s} {'hasil':9s} "
          f"{'iter':>4} {'temuan':16s} {'ms':>6}  catatan")
    print("-" * 96)

    hasil: list[Run] = []
    pertama: dict[tuple, Run] = {}
    for no, satu in enumerate(rencana, 1):
        r = jalankan(satu, no, log)

        if satu.get("ulang"):
            asal = pertama.get((r.skenario, r.sku, r.platform))
            if asal and (asal.iterasi, asal.temuan, asal.status) != (r.iterasi, r.temuan, r.status):
                r.masalah.append(f"tidak deterministik: run #{asal.no} "
                                 f"{asal.status}/{asal.iterasi}/{asal.temuan}")
        else:
            pertama.setdefault((r.skenario, r.sku, r.platform), r)

        hasil.append(r)
        catatan = "; ".join(r.masalah) if r.masalah else ("ok" if r.lolos else "")
        print(f"{r.no:3d} {r.skenario:9s} {r.sku:11s} {r.platform:12s} "
              f"{r.status:9s} {r.iterasi:4d} {str(r.temuan):16s} {r.detik*1000:6.0f}  {catatan}")

    # ------------------------------------------------------------------ ringkasan
    gagal = [r for r in hasil if not r.lolos]
    print("=" * 96)
    print(f"total run      : {len(hasil)}")
    print(f"lulus          : {len(hasil) - len(gagal)}")
    print(f"bermasalah     : {len(gagal)}")
    print(f"exception lolos: {sum(1 for r in hasil if r.status == 'EXCEPTION')}")

    print("\ncabang loop yang terlewati:")
    for (sk, st), n in sorted(Counter((r.skenario, r.status) for r in hasil).items()):
        print(f"  {sk:9s} -> {st:10s} {n:3d} run")

    print("\ndistribusi iterasi:")
    for it, n in sorted(Counter(r.iterasi for r in hasil).items()):
        print(f"  iterasi {it}: {n} run")

    print("\naturan yang paling sering muncul (di semua run):")
    aturan = Counter()
    for r in hasil:
        aturan.update(r.masalah)
    if aturan:
        for m, n in aturan.most_common(5):
            print(f"  {n:3d}x {m}")
    else:
        print("  — tidak ada pelanggaran invarian")

    ok, pesan, n = log.verify()
    print(f"\nrantai audit   : {'UTUH' if ok else 'RUSAK'} — {pesan} ({n} entri)")

    if gagal:
        print("\nDETAIL MASALAH")
        for r in gagal:
            print(f"  #{r.no} {r.skenario} {r.sku}/{r.platform}: {'; '.join(r.masalah)}")
            if r.error:
                print(f"       error: {r.error}")

    return 0 if not gagal else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
