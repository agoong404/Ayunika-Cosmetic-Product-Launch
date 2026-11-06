"""
run_bonus_tests.py — uji tiga kapabilitas bonus: C-15, C-17, C-18.

Dijalankan TERPISAH dari harness 26 kasus resmi, supaya angka 1100 eksekusi /
22 kasus yang sudah terekam di video tidak berubah. Ini bukti tambahan, bukan
klaim bahwa kasus resmi bertambah.

    cd engine && python run_bonus_tests.py

Rantai audit dan berkas usulan dialihkan ke folder sementara.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
for _p in (str(BASE), str(BASE / "engine")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_TMP = Path(tempfile.mkdtemp(prefix="lolos-bonus-"))
os.environ["HALAL_AUDIT_DIR"] = str(_TMP)
os.environ["LOLOS_PROPOSALS_DIR"] = str(_TMP)
KUNCI = "kunci-bonus-uji-0123456789abcdef"
os.environ["MCP_APPROVER_KEYS"] = json.dumps({
    "Agung": hashlib.sha256(KUNCI.encode("utf-8")).hexdigest(),
})

import multilingual as ml            # noqa: E402
import rule_proposals as rp          # noqa: E402
from mcp_server import tools         # noqa: E402

_GAGAL: list[str] = []
_LULUS = 0


def cek(nama: str, kondisi: bool, detail: object = "") -> None:
    global _LULUS
    if kondisi:
        _LULUS += 1
        print(f"  ok    {nama}")
    else:
        _GAGAL.append(nama)
        print(f"  GAGAL {nama}  {detail}")


def bagian(judul: str) -> None:
    print(f"\n{judul}")


SKU = "AY-SR-101"

# ---------------------------------------------------------------- C-15
bagian("C-15 · Tiga bahasa, satu himpunan fakta")
fakta = ml.muat()
cek("kamus memuat 4 SKU", len(fakta["sku"]) == 4, list(fakta["sku"]))
cek("tiga bahasa dideklarasikan", fakta["bahasa"] == ["id", "en", "zh"])

versi = {b: tools.get_localized_facts(SKU)["versi"][b] for b in ml.BAHASA}
cek("get_localized_facts menghasilkan 3 versi", len(versi) == 3)
for b in ml.BAHASA:
    cek(f"versi {b} tidak kosong", bool(versi[b].strip()))

r = tools.check_factual_consistency(SKU, versi)
cek("tiga versi kanonik KONSISTEN", r["konsisten"] and r["verdict"] == "KONSISTEN",
    r["temuan"])

# Angka yang berubah di satu bahasa harus ketahuan.
rusak = dict(versi)
rusak["en"] = versi["en"].replace("Rp149.000", "Rp139.000")
r2 = tools.check_factual_consistency(SKU, rusak)
cek("harga beda di EN → TIDAK_KONSISTEN", not r2["konsisten"], r2["temuan"])
cek("jenis temuan angka_asing / tidak_sejajar ada",
    any(t["jenis"] in ("angka_asing", "angka_tidak_sejajar") for t in r2["temuan"]),
    r2["temuan"])

# Klaim terlarang per bahasa (termasuk Mandarin).
larang = dict(versi)
larang["zh"] = versi["zh"] + " 清真配方。"
r3 = tools.check_factual_consistency(SKU, larang)
cek("klaim halal Mandarin tertangkap",
    any(t["jenis"] == "klaim_terlarang" and t["bahasa"] == "zh" for t in r3["temuan"]),
    r3["temuan"])

# Bahasa hilang → gagal tertutup.
r4 = tools.check_factual_consistency(SKU, {"id": versi["id"], "en": versi["en"]})
cek("versi ZH hilang → tidak konsisten", not r4["konsisten"])
cek("SKU asing tidak mengarang fakta",
    tools.get_localized_facts("SKU-ASING")["ok"] is False)

# ---------------------------------------------------------------- C-17
bagian("C-17 · Aset gambar + validasi teks via MCP")
tersedia, info = tools._ketersediaan_aset()
print(f"  (host: {info})")
if tersedia:
    b = tools.build_asset_card(SKU)
    cek("build_asset_card menghasilkan PNG", b.get("ok") is True and Path(b["berkas"]).exists(), b)
    cek("sidecar memuat 9 blok", len(b.get("blok", {})) == 9, list(b.get("blok", {})))

    v = tools.validate_asset_card(SKU)
    cek("kartu bersih → LULUS", v.get("status") == "LULUS", v.get("ringkas"))

    vs = tools.validate_asset_card(SKU, overrides={"harga": "Rp139.000"})
    cek("harga salah → TOLAK", vs.get("status") == "TOLAK", vs.get("ringkas"))

    vt = tools.validate_asset_card(SKU, potong={"aktif": {"lebar_px": 300}})
    cek("teks terpotong → TOLAK", vt.get("status") == "TOLAK", vt.get("ringkas"))
else:
    print("  LEWATI: Chrome/Tesseract tidak ada di host ini (perilaku fail-closed diuji)")
    b = tools.validate_asset_card(SKU)
    cek("tanpa OCR gagal tertutup, bukan crash", b.get("ok") is False, b)
    cek("alasan menyebut ketiadaan OCR/Chrome", "aset_tidak_tersedia" == b.get("error"), b)

cek("SKU lain ditolak, bukan dikarang",
    tools.build_asset_card("AY-BL-102")["ok"] is False)

# ---------------------------------------------------------------- C-18
bagian("C-18 · Suntingan manusia → usulan aturan → approval")
_asli = "Serum ini menyembuhkan jerawat dalam 3 hari."
_sunting = "Serum ini membantu mencerahkan kulit."
u = tools.propose_rule_from_edit(SKU, _asli, _sunting, "frasa_dilarang",
                                 "Manusia menghapus klaim terapi.")
cek("usulan terbentuk", u.get("ok") is True, u)
pid = u["usulan"]["id"]
cek("status awal PROPOSED", u["usulan"]["status"] == "PROPOSED")
cek("pola berasal dari kata yang dihapus", "menyembuhkan" in u["usulan"]["pola"].lower(),
    u["usulan"]["pola"])
cek("kutipan asli & suntingan tersimpan",
    u["usulan"]["kutipan_asli"] == _asli and u["usulan"]["kutipan_suntingan"] == _sunting)
import reviewer  # noqa: E402
_snapshot_rulebook = json.dumps(reviewer.RULEBOOK, sort_keys=True, ensure_ascii=False)
# ... dibandingkan ulang setelah persetujuan, di akhir bagian ini.
_ORIGINAL_RULEBOOK = _snapshot_rulebook

cek("kunci salah ditolak", tools.approve_rule_proposal(pid, "kunci-ngawur")["ok"] is False)
a = tools.approve_rule_proposal(pid, KUNCI, "Disetujui untuk ditinjau.")
cek("kunci benar → APPROVED", a.get("ok") is True and a["usulan"]["status"] == "APPROVED", a)
cek("approver diturunkan dari kunci", a["usulan"]["approver"] == "Agung")
cek("APPROVED tidak otomatis aktif", "belum aktif" in a["catatan"].lower(), a["catatan"])
cek("persetujuan kedua ditolak", tools.approve_rule_proposal(pid, KUNCI)["ok"] is False)

daftar = tools.list_rule_proposals("APPROVED")
cek("daftar APPROVED berisi 1", daftar["jumlah"] == 1, daftar)
md = rp.ekspor_markdown("APPROVED")
cek("ekspor markdown memuat id usulan", pid in md)

u2 = tools.propose_rule_from_edit(SKU, _asli, _sunting, "jenis_ngawur")
cek("jenis tidak sah ditolak", u2["ok"] is False)
cek("suntingan identik tidak menghasilkan usulan",
    tools.propose_rule_from_edit(SKU, _asli, _asli)["ok"] is False)
cek("RULEBOOK identik setelah seluruh alur usulan → approval (tidak ada auto-apply)",
    json.dumps(reviewer.RULEBOOK, sort_keys=True, ensure_ascii=False) == _ORIGINAL_RULEBOOK)

# ---------------------------------------------------------------- ringkas
print(f"\n{'=' * 62}")
if _GAGAL:
    print(f"GAGAL {len(_GAGAL)} dari {_LULUS + len(_GAGAL)}:")
    for g in _GAGAL:
        print(f"  - {g}")
    raise SystemExit(1)
print(f"LULUS {_LULUS}/{_LULUS} pemeriksaan bonus (C-15, C-17, C-18)")
raise SystemExit(0)
