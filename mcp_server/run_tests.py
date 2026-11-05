"""
run_tests.py — uji `mcp_server/tools.py` tanpa protokol, tanpa jaringan.

Pemakaian:
    .venv\\Scripts\\python.exe -m mcp_server.run_tests

Rantai audit dialihkan ke folder sementara supaya sesi asli di `engine/.audit/`
tidak tersentuh. Ini penting: mencampur entri uji ke rantai nyata membuat
`audit_verify` di demo tidak lagi bermakna.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TMP = Path(tempfile.mkdtemp(prefix="lolos-mcp-uji-"))
os.environ["HALAL_AUDIT_DIR"] = str(_TMP)

from mcp_server import tools  # noqa: E402

# Uji tidak boleh bergantung pada berkas kunci asli di root repo.
tools.KUNCI_PATH = _TMP / "kunci-tidak-ada"

SKU = "AY-SR-101"
PLATFORM = "tiktok"

# Satu kunci per approver. Server hanya menyimpan sha256-nya; kunci asli hanya
# ada di tangan manusianya (di uji ini: variabel di bawah).
KUNCI_AGUNG = "kunci-agung-uji-0123456789abcdef"
KUNCI_BUDI = "kunci-budi-uji-0123456789abcdef"
os.environ["MCP_APPROVER_KEYS"] = json.dumps({
    "Agung": hashlib.sha256(KUNCI_AGUNG.encode("utf-8")).hexdigest(),
    "Budi": hashlib.sha256(KUNCI_BUDI.encode("utf-8")).hexdigest(),
})

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


def _draf_contoh() -> str:
    """Fixture DRAFT-101_v1.md tanpa front-matter — seperti yang dikirim klien."""
    teks = (ROOT / "dataset_c" / "sample_drafts" / "DRAFT-101_v1.md").read_text(encoding="utf-8")
    return re.sub(r"^---.*?---\n", "", teks, count=1, flags=re.S).strip()


# --------------------------------------------------------------------------- 1
bagian("1. Katalog produk")
katalog = tools.list_products()
cek("list_products mengembalikan 4 SKU", katalog["jumlah"] == 4, katalog["jumlah"])
sku_terdaftar = {p["sku"] for p in katalog["produk"]}
cek("SKU AY-SR-101 ada", SKU in sku_terdaftar, sku_terdaftar)
cek("status halal AY-SR-101 belum ada",
    next(p for p in katalog["produk"] if p["sku"] == SKU)["status_halal"] == "BELUM_ADA")
cek("tidak ada path berkas yang bocor",
    "/" not in str(katalog) and "\\" not in str(katalog))


# --------------------------------------------------------------------------- 2
bagian("2. Konteks per SKU")
konteks = tools.get_context(SKU, PLATFORM)
cek("get_context ok", konteks.get("ok") is True)
cek("lembar produk termuat", "Bright Serum" in konteks["lembar_produk"])
cek("batas platform tiktok terbaca", konteks["batas"]["kata_maks"] == 175, konteks["batas"])
cek("AY-SR-101 tidak punya sertifikat", konteks["sertifikat"] == [])
cek("platform tak dikenal ditolak",
    tools.get_context(SKU, "facebook").get("error") == "platform_tidak_dikenal")
cek("SKU tak dikenal ditolak",
    tools.get_context("AY-XX-999", PLATFORM).get("error") == "sku_tidak_dikenal")


# --------------------------------------------------------------------------- 3
bagian("3. Rulebook")
rb = tools.get_rulebook()
cek("21 aturan", rb["jumlah"] == 21, rb["jumlah"])
cek("R-03 menyebut lapis-2",
    "lapis-2" in next(a for a in rb["aturan"] if a["rule_id"] == "R-03")["lapis"])
cek("rule_id asing dilaporkan", "R-99" in tools.get_rulebook(["R-99"])["tidak_dikenal"])


# --------------------------------------------------------------------------- 4
bagian("4. Rencana")
rencana = tools.plan_content(SKU, PLATFORM)
cek("plan_content ok", rencana.get("ok") is True, rencana)
plan = rencana["plan"]
cek("rencana lolos validasi", tools.validate_plan(plan)["valid"] is True)
cek("fakta_boleh terisi", len(plan["fakta_boleh"]) > 0)
cek("harga resmi terisi", plan["harga"] == "Rp149.000", plan["harga"])

rusak = dict(plan, fakta_boleh=[])
hasil_rusak = tools.validate_plan(rusak)
cek("rencana dengan fakta_boleh kosong ditolak", hasil_rusak["valid"] is False)
cek("alasan penolakan menyebut fakta_boleh",
    any("fakta_boleh" in m for m in hasil_rusak["masalah"]), hasil_rusak["masalah"])

cek("plan_content menolak platform asing",
    tools.plan_content(SKU, "facebook").get("error") == "platform_tidak_dikenal")


# --------------------------------------------------------------------------- 5
bagian("5. Menulis draf")
draf_hasil = tools.write_draft(plan)
cek("write_draft ok", draf_hasil.get("ok") is True, draf_hasil)
draf = draf_hasil["draft"]
cek("draf punya isi", len(draf) > 100, len(draf))
cek("hitungan kata konsisten", draf_hasil["kata"] == len(draf.split()))
cek("write_draft menolak rencana rusak",
    tools.write_draft(rusak).get("error") == "rencana_tidak_sah")


# --------------------------------------------------------------------------- 6
bagian("6. Review draf contoh (harus TOLAK)")
contoh = _draf_contoh()
hasil = tools.review_draft(contoh, SKU, PLATFORM, iteration=1)
cek("review_draft ok", hasil.get("ok") is True, hasil)
cek("verdict TOLAK", hasil["verdict"] == "TOLAK", hasil["verdict"])
cek("ada temuan", hasil["jumlah_temuan"] > 0)
aturan = {t["rule_id"] for t in hasil["temuan"]}
cek("R-07 superlatif tertangkap", "R-07" in aturan, sorted(aturan))
cek("R-13 pemutihan tertangkap", "R-13" in aturan, sorted(aturan))
cek("R-01 klaim terapeutik tertangkap", "R-01" in aturan, sorted(aturan))
cek("R-03 klaim halal tanpa sertifikat tertangkap", "R-03" in aturan, sorted(aturan))
# Span deterministik sebagian disintesis (mis. "4 emoji"), jadi bukan kutipan.
# Yang wajib berupa kutipan persis hanyalah temuan lapis-2.
span_penting = [t["span"] for t in hasil["temuan"] if t["rule_id"] in ("R-01", "R-07", "R-13")]
cek("kutipan temuan R-01/R-07/R-13 ada di draf",
    all(s in contoh for s in span_penting),
    [s for s in span_penting if s not in contoh])


# --------------------------------------------------------------------------- 7
bagian("7. Penjaga kutipan lapis-2")
palsu = [{"rule_id": "R-07", "span": "kalimat ini tidak ada di draf",
          "reason": "karangan", "fix": "hapus"}]
hasil_palsu = tools.review_draft(contoh, SKU, PLATFORM, findings=palsu)
cek("kutipan palsu dibuang", len(hasil_palsu["dibuang_llm"]) == 1)
cek("alasan penolakan jelas",
    hasil_palsu["dibuang_llm"][0].get("alasan_tolak") == "kutipan tidak ditemukan di draf",
    hasil_palsu["dibuang_llm"])

asli = [{"rule_id": "R-07", "span": "dijamin", "reason": "janji hasil", "fix": "hapus"}]
hasil_asli = tools.review_draft(contoh, SKU, PLATFORM, findings=asli)
cek("kutipan asli diterima", hasil_asli["dibuang_llm"] == [], hasil_asli["dibuang_llm"])

asing = [{"rule_id": "R-99", "span": "dijamin", "reason": "x", "fix": "y"}]
cek("rule_id asing dibuang",
    len(tools.review_draft(contoh, SKU, PLATFORM, findings=asing)["dibuang_llm"]) == 1)


# --------------------------------------------------------------------------- 8
bagian("8. Batas masukan")
cek("draf kosong ditolak",
    tools.review_draft("   ", SKU, PLATFORM).get("error") == "draf_kosong")
cek("draf terlalu panjang ditolak",
    tools.review_draft("a" * 20_001, SKU, PLATFORM).get("error") == "draf_terlalu_panjang")
cek("findings terlalu banyak ditolak",
    tools.review_draft(contoh, SKU, PLATFORM,
                       findings=[dict(asli[0])] * 51).get("error") == "findings_terlalu_banyak")


# --------------------------------------------------------------------------- 9
bagian("9. SKU asing tidak boleh dianggap lulus")
# Draf bersih dari Writer, dinilai untuk SKU yang tidak ada di registri.
hasil_asing = tools.review_draft(draf, "AY-XX-999", PLATFORM)
cek("verdict PERLU_DATA", hasil_asing["verdict"] == "PERLU_DATA", hasil_asing["verdict"])
cek("PERLU_DATA bukan LOLOS", hasil_asing["verdict"] != "LOLOS")
cek("catatan keterbatasan diisi", len(hasil_asing["catatan"]) > 0)
# Draf yang melanggar tetap TOLAK walau SKU-nya asing: pelanggaran teks tidak
# butuh data produk untuk terdeteksi.
hasil_asing_kotor = tools.review_draft(contoh, "AY-XX-999", PLATFORM)
cek("draf melanggar tetap TOLAK meski SKU asing",
    hasil_asing_kotor["verdict"] == "TOLAK", hasil_asing_kotor["verdict"])


# --------------------------------------------------------------------------- 10
bagian("10. Siklus penuh")
siklus = tools.run_cycle(SKU, PLATFORM)
cek("run_cycle ok", siklus.get("ok") is True, siklus)
cek("status bukan TERBIT", siklus["status"] != "TERBIT", siklus["status"])
cek("status salah satu dari LOLOS/PERLU_DATA/ESKALASI",
    siklus["status"] in ("LOLOS", "PERLU_DATA", "ESKALASI"), siklus["status"])
cek("riwayat terisi", len(siklus["riwayat"]) >= 1)
cek("setiap iterasi punya verdict",
    all("verdict" in h for h in siklus["riwayat"]))
print(f"        status akhir: {siklus['status']} setelah {siklus['iterasi']} iterasi")


# --------------------------------------------------------------------------- 11
bagian("11. Gerbang approval")
usul = tools.request_approval(SKU, PLATFORM, "konten uji untuk gerbang approval")
cek("request_approval ok", usul.get("ok") is True, usul)
cek("status PROPOSED", usul["status"] == "PROPOSED", usul["status"])
plan_id = usul["plan_id"]
cek("plan_id berawalan PLAN-", plan_id.startswith("PLAN-"), plan_id)

salah = tools.approve_publication(plan_id, "kunci-yang-salah")
cek("kunci salah ditolak",
    salah.get("ok") is False and salah["error"] == "approval_key_salah", salah)

kosong = tools.approve_publication(plan_id, "   ")
cek("kunci kosong ditolak", kosong.get("error") == "approval_key_kosong", kosong)

# Kunci salah tidak boleh membocorkan plan mana yang ada: kunci diperiksa
# lebih dulu, jadi jawabannya approval_key_salah, bukan plan_tidak_ada.
oracle = tools.approve_publication("PLAN-00000000", "kunci-yang-salah")
cek("plan tidak ada tidak bocor lewat kunci salah",
    oracle.get("error") == "approval_key_salah", oracle)

# Mendaftarkan nama pemohon sebagai approver adalah salah konfigurasi: ditolak
# saat registri dimuat, bukan menunggu gerbang menangkapnya nanti.
_reg_awal = os.environ["MCP_APPROVER_KEYS"]
os.environ["MCP_APPROVER_KEYS"] = json.dumps({
    tools.ACTOR: hashlib.sha256(KUNCI_AGUNG.encode("utf-8")).hexdigest(),
})
swa_reg = tools.approve_publication(plan_id, KUNCI_AGUNG)
cek("registri berisi nama pemohon ditolak saat dimuat",
    swa_reg.get("error") == "approval_belum_dikonfigurasi", swa_reg)
os.environ["MCP_APPROVER_KEYS"] = _reg_awal

# Lapisan terakhir tetap di gerbang: kalaupun registri lolos, pemohon tidak
# boleh menyetujui aksinya sendiri. Diuji langsung ke ApprovalGate.
try:
    tools._GATE.approve(plan_id, tools.ACTOR)
    cek("gerbang menolak swa-approval (lapisan terakhir)", False, "tidak raise")
except PermissionError:
    cek("gerbang menolak swa-approval (lapisan terakhir)", True)

sah = tools.approve_publication(plan_id, KUNCI_AGUNG, "sudah diperiksa manual")
cek("approver manusia diterima", sah.get("ok") is True, sah)
cek("status APPROVED", sah["status"] == "APPROVED", sah["status"])
cek("nama approver diturunkan dari kunci", sah["approver"] == "Agung", sah["approver"])

ulang = tools.approve_publication(plan_id, KUNCI_BUDI)
cek("approval kedua ditolak walau approver lain sah",
    ulang.get("ok") is False and ulang["error"] == "approval_ditolak", ulang)

hilang = tools.approve_publication("PLAN-00000000", KUNCI_AGUNG)
cek("plan tidak ada ditolak", hilang.get("error") == "plan_tidak_ada", hilang)

# ---- legacy: kunci lama tanpa nama pemilik tidak boleh jadi identitas bebas ----
reg_lama = os.environ.pop("MCP_APPROVER_KEYS")
os.environ["MCP_APPROVAL_KEY"] = "kunci-lama-uji-0123456789abcdef"
lama = tools.approve_publication(plan_id, "kunci-lama-uji-0123456789abcdef")
cek("kunci lama tanpa nama pemilik ditolak",
    lama.get("error") == "approval_belum_dikonfigurasi", lama)

os.environ["MCP_APPROVAL_KEY_OWNER"] = "Budi"
usul2 = tools.request_approval(SKU, PLATFORM, "konten uji jalur legacy")
plan2 = usul2["plan_id"]
lama2 = tools.approve_publication(plan2, "kunci-lama-uji-0123456789abcdef")
cek("kunci lama + nama pemilik diterima", lama2.get("ok") is True, lama2)
cek("nama dari MCP_APPROVAL_KEY_OWNER", lama2["approver"] == "Budi", lama2["approver"])
del os.environ["MCP_APPROVAL_KEY"]
del os.environ["MCP_APPROVAL_KEY_OWNER"]

# ---- registri rusak / salah tempel harus keras, bukan diam-diam ----
os.environ["MCP_APPROVER_KEYS"] = "{bukan json"
rusak = tools.approve_publication(plan_id, KUNCI_AGUNG)
cek("registri rusak ditolak dengan pesan jelas",
    rusak.get("error") == "approval_belum_dikonfigurasi", rusak)

os.environ["MCP_APPROVER_KEYS"] = json.dumps({"Agung": KUNCI_AGUNG})  # kunci asli, bukan hash
tempel = tools.approve_publication(plan_id, KUNCI_AGUNG)
cek("menempel kunci asli ditolak, bukan diam-diam",
    tempel.get("error") == "approval_belum_dikonfigurasi", tempel)

# ---- tanpa sumber registri apa pun: approval mustahil ----
del os.environ["MCP_APPROVER_KEYS"]
path_reg_lama = tools.APPROVER_KEYS_PATH
tools.APPROVER_KEYS_PATH = _TMP / "approver-tidak-ada"
usul3 = tools.request_approval(SKU, PLATFORM, "konten uji tanpa registri")
tanpa = tools.approve_publication(usul3["plan_id"], KUNCI_AGUNG)
cek("tanpa registri server, approval mustahil",
    tanpa.get("error") == "approval_belum_dikonfigurasi", tanpa)

# ---- cadangan berkas: dipakai bila host tidak meneruskan blok `env` ----
berkas_reg = _TMP / "approver-berkas"
berkas_reg.write_text(json.dumps({
    "Sari": hashlib.sha256(KUNCI_BUDI.encode("utf-8")).hexdigest(),
}), encoding="utf-8")
tools.APPROVER_KEYS_PATH = berkas_reg
usul4 = tools.request_approval(SKU, PLATFORM, "konten uji registri dari berkas")
dari_berkas = tools.approve_publication(usul4["plan_id"], KUNCI_BUDI)
cek("registri dibaca dari berkas bila env kosong", dari_berkas.get("ok") is True, dari_berkas)
cek("nama approver dari berkas", dari_berkas["approver"] == "Sari", dari_berkas["approver"])
tools.APPROVER_KEYS_PATH = path_reg_lama
os.environ["MCP_APPROVER_KEYS"] = reg_lama

# Percobaan yang ditolak harus meninggalkan jejak, kalau tidak tebakan kunci
# berulang tidak akan terlihat sama sekali di rantai audit.
blokir = [e for e in tools.audit_tail(100)["entri"] if e["action"] == "approval_blocked"]
alasan = {e["meta"].get("alasan") for e in blokir}
cek("penolakan tercatat di audit", len(blokir) >= 7, len(blokir))
cek("alasan kunci salah tercatat", "kunci approval tidak cocok" in alasan, alasan)
cek("alasan swa-approval tercatat",
    "pemohon tidak boleh menyetujui aksinya sendiri" in alasan, alasan)
cek("alasan kunci kosong tercatat", "kunci approval kosong" in alasan, alasan)
cek("alasan plan tidak ada tercatat", "plan tidak ada" in alasan, alasan)
cek("penolakan berstatus REFUSED", all(e["result"] == "REFUSED" for e in blokir))

isi_audit = (_TMP / "audit.jsonl").read_text(encoding="utf-8")
cek("kunci yang dicoba tidak ikut tercatat", "kunci-yang-salah" not in isi_audit)
for k in (KUNCI_AGUNG, KUNCI_BUDI, "kunci-lama-uji-0123456789abcdef"):
    cek(f"kunci {k[:10]}… tidak pernah tercatat", k not in isi_audit)
cek("hash kunci juga tidak tercatat",
    hashlib.sha256(KUNCI_AGUNG.encode("utf-8")).hexdigest() not in isi_audit)

# Cadangan berkas kunci lama (legacy): dipakai bila env tidak diteruskan host.
kunci_berkas = _TMP / "kunci-berkas"
kunci_berkas.write_text("kunci-dari-berkas", encoding="utf-8")
tools.KUNCI_PATH = kunci_berkas
cek("kunci legacy dibaca dari berkas bila env kosong",
    tools._kunci_approval() == "kunci-dari-berkas")
tools.KUNCI_PATH = _TMP / "kunci-tidak-ada"


# --------------------------------------------------------------------------- 12
bagian("12. Audit")
verifikasi = tools.audit_verify()
cek("rantai utuh", verifikasi["utuh"] is True, verifikasi)
cek("ada entri", verifikasi["jumlah_entri"] > 0, verifikasi["jumlah_entri"])
print(f"        {verifikasi['jumlah_entri']} entri · {verifikasi['pesan']}")

ekor = tools.audit_tail(5)
cek("audit_tail mengembalikan <= 5", ekor["dikembalikan"] <= 5, ekor["dikembalikan"])
cek("audit_tail membatasi di 100", tools.audit_tail(9999)["dikembalikan"] <= 100)

tindakan = {e["action"] for e in tools.audit_tail(100)["entri"]}
cek("plan_propose tercatat", "plan_propose" in tindakan, tindakan)
cek("plan_approve tercatat", "plan_approve" in tindakan, tindakan)
cek("review tercatat", "review" in tindakan, tindakan)


# --------------------------------------------------------------------------- ringkas
print("\n" + "-" * 62)
if _GAGAL:
    print(f"GAGAL {len(_GAGAL)} dari {_LULUS + len(_GAGAL)} pemeriksaan:")
    for nama in _GAGAL:
        print(f"  · {nama}")
    print(f"audit uji: {_TMP}")
    raise SystemExit(1)
print(f"LULUS {_LULUS}/{_LULUS} pemeriksaan")
print(f"audit uji (dibuang): {_TMP}")
