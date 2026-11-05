"""
workbuddy.py — menjalankan loop Challenge C dengan WorkBuddy sebagai modelnya.

Kenapa jembatan, bukan API:
  WorkBuddy tidak menerbitkan API key. Yang tersedia adalah model yang sudah
  terpasang di aplikasi ini. Jadi jalurnya bukan HTTP, melainkan **percakapan**:
  skrip mencetak prompt, model WorkBuddy menjawab, jawabannya disimpan, lalu
  Reviewer menilainya. Semua langkah tetap tercatat di audit chain.

Perintah:

    start <SKU> <platform>     buat sesi + cetak prompt Planner
    save plan  <berkas.json>   simpan rencana (divalidasi kontrak)
    next                       cetak prompt berikutnya (Writer atau lapis-2)
    save draft <berkas.md>     simpan draf -> jalankan lapis-1
    save findings <berkas>     simpan penilaian lapis-2 -> verdict final
    skip                       lewati lapis-2 (tercatat sebagai dilewati)

Satu putaran review terdiri dari dua langkah karena Reviewer punya dua lapis:
kode (pasti, murah) lalu model (untuk yang butuh pemahaman bahasa). Lapis-1
dijalankan lebih dulu supaya temuannya sudah terlihat sebelum lapis-2 dinilai.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from agents.contract import ContractError, Plan, parse_json_loose, validate_draft  # noqa: E402
from agents.planner import PlannerAgent                                          # noqa: E402
from agents.writer import WriterAgent, _bersih                                    # noqa: E402
from governance import ApprovalGate, AuditLog                                     # noqa: E402
from layer2 import Layer2                                                         # noqa: E402
from reviewer import Reviewer                                                     # noqa: E402

WB = Path(__file__).resolve().parent / ".wb"
SESI = WB / "session.json"
MAX_ITER = 3


# --------------------------------------------------------------------------- state
def _kosong(sku: str, platform: str) -> dict:
    return {"sku": sku, "platform": platform, "tahap": "plan", "iterasi": 1,
            "plan": None, "feedback": None, "riwayat": [], "status": "BERJALAN",
            "draf_terakhir": "", "lapis2": []}


def _muat() -> dict | None:
    if not SESI.exists():
        return None
    return json.loads(SESI.read_text(encoding="utf-8"))


def _simpan(s: dict) -> None:
    WB.mkdir(exist_ok=True)
    SESI.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def _baca(berkas: str) -> str:
    if berkas == "-":
        return sys.stdin.read()
    return Path(berkas).read_text(encoding="utf-8")


def _kotak(judul: str, isi: str) -> None:
    print("\n" + "=" * 78)
    print(judul)
    print("=" * 78)
    print(isi.strip())
    print("=" * 78 + "\n")


# --------------------------------------------------------------------------- prompt
def _prompt_planner(s: dict) -> None:
    p = PlannerAgent()
    system, user = p.build_prompt(s["sku"], s["platform"])
    _kotak("PROMPT SISTEM (untuk model)", system)
    _kotak("PROMPT PENGGUNA (kirim ini)", user)
    print("Balasan model: objek JSON rencana.")
    print("Simpan ke berkas, lalu:  python -m agents.workbuddy save plan <berkas>\n")


def _prompt_writer(s: dict) -> None:
    plan = Plan.from_dict(s["plan"], pembuat="planner-agent")
    system, user = WriterAgent().build_prompt(plan, s["feedback"], s["iterasi"])
    _kotak("PROMPT SISTEM (untuk model)", system)
    _kotak(f"PROMPT PENGGUNA — iterasi {s['iterasi']}", user)
    if s["feedback"]:
        print(f"Catatan Reviewer yang harus diperbaiki: "
              f"{sorted({f['rule_id'] for f in s['feedback']})}")
    print("Balasan model: teks konten saja.")
    print("Simpan ke berkas, lalu:  python -m agents.workbuddy save draft <berkas>\n")


def _prompt_layer2(s: dict) -> None:
    l2 = Layer2(reviewer=Reviewer())
    system, user = l2.build_prompt(s["draf_terakhir"], s["sku"], s["platform"])
    _kotak("PROMPT SISTEM — Reviewer lapis-2", system)
    _kotak("PROMPT PENGGUNA — lapis-2", user)
    print('Balasan model: {"findings": [...]} — span harus disalin persis dari draf.')
    print("Simpan ke berkas, lalu:  python -m agents.workbuddy save findings <berkas>")
    print("Atau lewati:             python -m agents.workbuddy skip\n")


# --------------------------------------------------------------------------- aksi
def cmd_start(sku: str, platform: str) -> int:
    reg = PlannerAgent()
    if sku not in reg.products:
        print(f"SKU {sku} tidak ada. Pilihan: {', '.join(reg.products)}")
        return 1
    s = _kosong(sku, platform)
    _simpan(s)
    print(f"Sesi dibuat: {sku} / {platform} · audit: {AuditLog().path}")
    _prompt_planner(s)
    return 0


def cmd_save_plan(berkas: str) -> int:
    s = _muat()
    if not s:
        print("Belum ada sesi. Jalankan: python -m agents.workbuddy start <SKU> <platform>")
        return 1
    try:
        data = parse_json_loose(_baca(berkas))
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Jawaban model bukan JSON yang sah: {e}")
        return 1
    try:
        plan = PlannerAgent().plan_from_model(data, s["sku"], s["platform"], mode="workbuddy")
    except ContractError as e:
        print(f"Rencana ditolak kontrak — {e}")
        print("Perbaiki lalu simpan ulang. Tidak ada yang masuk pipeline.")
        return 1
    s["plan"] = plan.to_dict()
    s["tahap"] = "draft"
    _simpan(s)
    print(f"Rencana diterima · {len(plan.fakta_boleh)} fakta boleh · "
          f"{len(plan.fakta_dilarang)} fakta dilarang")
    print("Lanjut: python -m agents.workbuddy next")
    return 0


def cmd_save_draft(berkas: str) -> int:
    """Simpan draf, jalankan lapis-1 saja. Verdict final menunggu lapis-2."""
    s = _muat()
    if not s:
        print("Belum ada sesi.")
        return 1
    if not s["plan"]:
        print("Rencana belum ada. Simpan rencana lebih dulu.")
        return 1

    plan = Plan.from_dict(s["plan"], pembuat="planner-agent")
    try:
        draf = validate_draft(_bersih(_baca(berkas)), plan, "workbuddy")
    except ContractError as e:
        print(f"Draf ditolak kontrak — {e}")
        return 1

    det = Reviewer().review(draf, s["sku"], s["platform"], s["iterasi"], log=False)
    s["draf_terakhir"] = draf
    s["tahap"] = "findings"
    _simpan(s)

    print("LAPIS-1 (kode)")
    print(det.report())
    print(f"\n{len(det.checks)} pemeriksaan · {len(det.violations)} temuan")
    if det.violations:
        print("\nLapis-1 sudah menolak. Lapis-2 tetap dijalankan supaya temuannya")
        print("lengkap dalam satu putaran — bukan untuk membatalkan penolakan.")
    print("\nLanjut: python -m agents.workbuddy next   (prompt lapis-2)")
    return 0


def _finalisasi(s: dict, draf: str, temuan_l2: list[dict] | None,
                catatan: str = "") -> int:
    """Verdict final: lapis-1 + lapis-2, lalu keputusan loop."""
    log = AuditLog()
    reviewer = Reviewer(audit=log)
    hasil = reviewer.review(draf, s["sku"], s["platform"], s["iterasi"],
                            llm_findings=temuan_l2 or None)

    print("\nVERDICT FINAL (lapis-1 + lapis-2)" if temuan_l2
          else "\nVERDICT FINAL (lapis-1 saja)")
    print(hasil.report())
    print(f"\n{len(hasil.checks)} pemeriksaan · {len(hasil.violations)} temuan"
          + (f" · {len(hasil.dropped_llm)} temuan model dibuang" if hasil.dropped_llm else ""))
    if catatan:
        print(catatan)

    s["lapis2"].append({"iterasi": s["iterasi"],
                        "diterima": len(temuan_l2 or []),
                        "dibuang": len(hasil.dropped_llm)})
    s["riwayat"].append({"iterasi": s["iterasi"], "verdict": hasil.verdict,
                         "temuan": len(hasil.violations),
                         "aturan": sorted({v.rule_id for v in hasil.violations})})

    keputusan = reviewer.decide_next(hasil)

    if keputusan["aksi"] == "SELESAI":
        gate = ApprovalGate(log)
        p = gate.propose("workbuddy-agent", "publikasikan",
                         {"sku": s["sku"], "platform": s["platform"], "konten": draf})
        gate.approve(p["plan_id"], "EMP-014", "disetujui setelah review dua lapis")
        gate.execute(p["plan_id"], "workbuddy-agent", lambda x: None)
        s.update(status="TERBIT", plan_id=p["plan_id"], konten_final=draf, tahap="selesai")
        _simpan(s)
        final = WB / "konten-final.md"
        final.write_text(draf, encoding="utf-8")
        print(f"\nLOLOS di iterasi {s['iterasi']} · terbit dengan plan {p['plan_id']}")
        print(f"Konten final: {final}")
        return 0

    if keputusan["aksi"] == "ESKALASI":
        s.update(status="ESKALASI", tahap="selesai",
                 feedback=[v.as_dict() for v in hasil.violations])
        _simpan(s)
        print(f"\nESKALASI · batas {MAX_ITER} iterasi · sisa: {keputusan['sisa_masalah']}")
        print("Tidak ada yang terbit. Ini perilaku yang benar, bukan kegagalan.")
        return 0

    s["feedback"] = [v.as_dict() for v in hasil.violations]
    s["iterasi"] += 1
    s["tahap"] = "draft"
    _simpan(s)
    print(f"\nREVISI · lanjut ke iterasi {s['iterasi']} dari {MAX_ITER}")
    print("Lanjut: python -m agents.workbuddy next")
    return 0


def cmd_save_findings(berkas: str) -> int:
    s = _muat()
    if not s:
        print("Belum ada sesi.")
        return 1
    if s["tahap"] != "findings" or not s["draf_terakhir"]:
        print("Belum ada draf yang menunggu lapis-2. Jalankan: save draft <berkas>")
        return 1

    l2 = Layer2(reviewer=Reviewer())
    out = l2.from_text(s["draf_terakhir"], _baca(berkas))

    print(f"Lapis-2: {out['mentah']} temuan mentah · "
          f"{len(out['diterima'])} diterima · {len(out['dibuang'])} dibuang")
    for d in out["dibuang"]:
        print(f"  dibuang : {d.get('rule_id', '-')} — {d.get('alasan_tolak', '?')}"
              f"  “{str(d.get('span', ''))[:48]}”")
    for a in out["diterima"]:
        print(f"  diterima: {a['rule_id']} “{a['span'][:56]}”")
    if out["error"]:
        print(f"\nCatatan: {out['error']}")

    return _finalisasi(s, s["draf_terakhir"], out["diterima"])


def cmd_skip() -> int:
    s = _muat()
    if not s:
        print("Belum ada sesi.")
        return 1
    if s["tahap"] != "findings" or not s["draf_terakhir"]:
        print("Tidak ada draf yang menunggu lapis-2.")
        return 1
    AuditLog().append("workbuddy-agent", "layer2_skipped",
                      f"{s['sku']}/{s['platform']}", "SKIP",
                      meta={"iterasi": s["iterasi"]})
    print("Lapis-2 dilewati. Keputusan hanya memakai lapis-1 — dan itu tercatat")
    print("di audit log sebagai layer2_skipped, bukan disembunyikan.")
    return _finalisasi(s, s["draf_terakhir"], None)


def cmd_next() -> int:
    s = _muat()
    if not s:
        print("Belum ada sesi. Jalankan: python -m agents.workbuddy start <SKU> <platform>")
        return 1
    if s["status"] != "BERJALAN":
        print(f"Sesi sudah selesai: {s['status']}")
        return 0
    if s["tahap"] == "findings" and s["draf_terakhir"]:
        _prompt_layer2(s)
    elif not s["plan"]:
        _prompt_planner(s)
    else:
        _prompt_writer(s)
    return 0


def cmd_status() -> int:
    s = _muat()
    if not s:
        print("Belum ada sesi.")
        return 1
    print(f"{s['sku']} / {s['platform']} · {s['status']} · iterasi {s['iterasi']}/{MAX_ITER}")
    for h in s["riwayat"]:
        print(f"  iterasi {h['iterasi']}: {h['verdict']:5s} · {h['temuan']} temuan {h['aturan']}")
    for l in s.get("lapis2", []):
        print(f"  lapis-2 iterasi {l['iterasi']}: {l['diterima']} diterima, "
              f"{l['dibuang']} dibuang")
    if s.get("plan_id"):
        print(f"  plan: {s['plan_id']}")
    if s["status"] == "BERJALAN":
        tahap = {"plan": "simpan rencana", "draft": "tulis draf",
                 "findings": "nilai lapis-2"}.get(s["tahap"], s["tahap"])
        print(f"  berikutnya: {tahap}")
    return 0


def cmd_reset() -> int:
    if SESI.exists():
        SESI.unlink()
    print("Sesi dihapus. Audit log TIDAK dihapus — itu append-only.")
    return 0


# --------------------------------------------------------------------------- CLI
def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "start" and len(argv) >= 3:
        return cmd_start(argv[1], argv[2])
    if cmd == "save" and len(argv) >= 3:
        jenis, berkas = argv[1], argv[2]
        if jenis == "plan":
            return cmd_save_plan(berkas)
        if jenis == "draft":
            return cmd_save_draft(berkas)
        if jenis == "findings":
            return cmd_save_findings(berkas)
        print("Jenis tidak dikenal. Pakai: save plan|draft|findings <berkas>")
        return 1
    if cmd == "skip":
        return cmd_skip()
    if cmd == "next":
        return cmd_next()
    if cmd == "status":
        return cmd_status()
    if cmd == "reset":
        return cmd_reset()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
