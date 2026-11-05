"""
tools.py — dua belas fungsi biasa di atas `engine/` dan `agents/`.

Aturan yang dipegang berkas ini:

  1. TIDAK mengimpor `mcp`. Semua di sini bisa dipanggil dari skrip uji tanpa
     server, tanpa transport, tanpa klien.
  2. TIDAK mencetak apa pun ke stdout. Untuk transport stdio, stdout adalah
     kabel protokol; satu `print()` merusaknya. Diagnosis memakai `logging`.
  3. TIDAK menilai ulang. Semua keputusan tetap milik `engine/reviewer.py` dan
     `engine/governance.py`; di sini hanya pemanggilan dan pembungkusan hasil.
  4. TIDAK menerbitkan. Rantai berhenti di APPROVED.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import json
import os
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
for _p in (str(ROOT), str(ENGINE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from governance import ApprovalGate, AuditLog                    # noqa: E402
from reviewer import RULEBOOK, Reviewer                          # noqa: E402
from agents.contract import (                                    # noqa: E402
    BATAS,
    PLATFORMS,
    ContractError,
    Plan,
    validate_plan as _validate_plan,
)
from agents.planner import PlannerAgent                          # noqa: E402
from agents.writer import WriterAgent                            # noqa: E402

DATA = ROOT / "dataset_c"

# Batas masukan. Server menolak di atas angka ini, bukan memotong diam-diam.
MAX_DRAFT = 20_000
MAX_FINDINGS = 50
MAX_AUDIT_TAIL = 100
MAX_ITERASI = 3

# Identitas pemohon. Tidak boleh dipakai sebagai nama approver: gerbang menolak
# persetujuan diri sendiri, dan nama approver kini DITURUNKAN dari kunci.
ACTOR = "workbuddy-agent"

# AuditLog mengasumsikan SATU penulis dan menyimpan cache entri terakhir.
# Semua panggilan yang bisa menulis diserialisasi lewat kunci ini.
_LOCK = threading.Lock()


def _audit_path() -> Path:
    """HALAL_AUDIT_DIR memindahkan rantai audit; dipakai uji agar tidak mengotori sesi asli."""
    folder = Path(os.environ.get("HALAL_AUDIT_DIR", str(ENGINE / ".audit")))
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "audit.jsonl"


# Cadangan bila host tidak meneruskan blok `env` ke proses anak: kunci dibaca
# dari berkas di root repo. Berkas ini masuk .gitignore dan tidak pernah dicetak.
KUNCI_PATH = ROOT / ".approval_key"


def _kunci_approval() -> str:
    """Kunci approval: environment lebih dulu, lalu berkas lokal. Kosong = gate mati."""
    dari_env = os.environ.get("MCP_APPROVAL_KEY", "").strip()
    if dari_env:
        return dari_env
    if KUNCI_PATH.exists():
        return KUNCI_PATH.read_text(encoding="utf-8").strip()
    return ""


# --------------------------------------------------------------------------- kunci per approver
# Satu kunci per manusia. Server TIDAK menyimpan kunci aslinya — hanya SHA-256
# hex-nya. Nama approver DITURUNKAN dari kunci yang dikirim, bukan diklaim
# pemanggil. Dengan itu "approver ≠ pemohon" di ApprovalGate menjadi terbukti
# (agen tidak bisa menghasilkan kunci manusia kedua), bukan sekadar nama bebas
# yang diketik seperti sebelumnya.
#
# Sumber registri, berurutan:
#   1. MCP_APPROVER_KEYS  — env, JSON {"Nama": "<sha256(kunci)>"}
#   2. .approver_keys     — berkas JSON sama di root repo (gitignored), cadangan
#                           bila host tidak meneruskan blok `env`
#   3. Legacy             — MCP_APPROVAL_KEY + MCP_APPROVAL_KEY_OWNER (satu entri)
APPROVER_KEYS_PATH = ROOT / ".approver_keys"
OWNER_LEGACY_ENV = "MCP_APPROVAL_KEY_OWNER"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha256(teks: str) -> str:
    return hashlib.sha256(teks.encode("utf-8")).hexdigest()


def _registry_dari_json(mentah: str, sumber: str) -> tuple[dict[str, str], str]:
    """
    JSON {nama: sha256} -> (registri, pesan_salah).

    Nilai yang bukan hex64 ditolak dengan nama pemiliknya: salah tempel kunci
    asli bukan hex64, jadi tertangkap di sini — bukan diam-diam menjadi kunci
    yang tidak pernah cocok.
    """
    try:
        data = json.loads(mentah)
    except json.JSONDecodeError as e:
        return {}, f"{sumber} bukan JSON sah: {e}"
    if not isinstance(data, dict) or not data:
        return {}, (f"{sumber} harus objek JSON tidak kosong: "
                    '{"Nama": "<sha256(kunci)>"}')
    reg: dict[str, str] = {}
    for nama, nilai in data.items():
        nama = str(nama).strip()
        nilai = str(nilai).strip().lower()
        if not nama:
            return {}, f"{sumber} memuat kunci objek (nama) yang kosong"
        if nama == ACTOR:
            return {}, (f"{sumber} memuat approver bernama '{ACTOR}'. Nama itu "
                        "milik pemohon; gerbang akan menolak persetujuannya.")
        if not HEX64.match(nilai):
            return {}, (f"{sumber}: nilai untuk '{nama}' bukan sha256 hex 64 "
                        "karakter. Jangan tempel kunci aslinya — tempel hash-nya "
                        "(python -m mcp_server.gen_approver_keys Nama).")
        reg[nama] = nilai
    return reg, ""


def _daftar_approver() -> tuple[dict[str, str], str]:
    """(registri nama -> sha256, pesan_salah). Kosong tanpa pesan = belum dikonfigurasi."""
    mentah = os.environ.get("MCP_APPROVER_KEYS", "").strip()
    if mentah:
        return _registry_dari_json(mentah, "MCP_APPROVER_KEYS")
    if APPROVER_KEYS_PATH.exists():
        try:
            isi = APPROVER_KEYS_PATH.read_text(encoding="utf-8").strip()
        except OSError as e:
            return {}, f".approver_keys tidak bisa dibaca: {e}"
        if isi:
            return _registry_dari_json(isi, ".approver_keys")
    # Legacy: kunci lama tanpa nama pemilik tidak boleh diam-diam menjadi
    # identitas bebas — justru itu masalah yang perubahan ini tutup.
    kunci = _kunci_approval()
    if kunci:
        pemilik = os.environ.get(OWNER_LEGACY_ENV, "").strip()
        if not pemilik:
            return {}, ("MCP_APPROVAL_KEY terpasang tetapi MCP_APPROVAL_KEY_OWNER "
                        "kosong. Sebut nama pemilik kunci itu, atau migrasi ke "
                        "MCP_APPROVER_KEYS (python -m mcp_server.gen_approver_keys).")
        return {pemilik: _sha256(kunci)}, ""
    return {}, ""


def registri_siap() -> bool:
    """True bila server punya sumber registri approver yang sah. Dipakai __main__."""
    daftar, salah = _daftar_approver()
    return bool(daftar) and not salah


_LOG = AuditLog(path=_audit_path())
_GATE = ApprovalGate(_LOG)
_REVIEWER = Reviewer(audit=_LOG)

# Sengaja tanpa LLM. Tool harus selesai jauh di bawah timeout 30 detik WorkBuddy,
# dan panggilan model dari dalam tool membuat waktu jawab tidak terbatas.
_PLANNER = PlannerAgent()
_WRITER = WriterAgent()


# --------------------------------------------------------------------------- bantu
def _rows(nama: str) -> list[dict]:
    with open(DATA / nama, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _rupiah(nilai) -> str:
    angka = re.sub(r"\D", "", str(nilai or ""))
    if not angka:
        return ""
    return "Rp" + f"{int(angka):,}".replace(",", ".")


def _gagal(kode: str, pesan: str, **tambahan) -> dict:
    return {"ok": False, "error": kode, "pesan": pesan, **tambahan}


def _iterasi(n) -> int:
    try:
        k = int(n)
    except (TypeError, ValueError):
        return 1
    return max(1, min(k, MAX_ITERASI))


# --------------------------------------------------------------------------- 1. katalog
def list_products() -> dict:
    """Daftar SKU di registri, termasuk yang status halalnya belum beres."""
    produk = []
    for r in _rows("products.csv"):
        promo = (r.get("harga_promo") or "").strip()
        produk.append({
            "sku": r["sku"],
            "nama": r["nama_produk"],
            "kategori": r.get("kategori", ""),
            "isi": r.get("isi", ""),
            "harga": _rupiah(r.get("harga")),
            "harga_promo": _rupiah(promo) if promo else None,
            "kuota_promo": (r.get("kuota_promo") or "").strip() or None,
            "bpom": r.get("notifikasi_bpom", ""),
            "status_halal": r.get("cert_status", ""),
            "catatan": r.get("catatan", ""),
        })
    return {
        "jumlah": len(produk),
        "produk": produk,
        "platform": list(PLATFORMS),
        "catatan": "status_halal BELUM_ADA atau PENGAJUAN berarti klaim halal belum boleh dipakai.",
    }


# --------------------------------------------------------------------------- 2. konteks
def get_context(sku: str, platform: str) -> dict:
    """Bundel konteks Planner: registri, sertifikat, lembar produk, brief, batas platform."""
    if platform not in PLATFORMS:
        return _gagal("platform_tidak_dikenal",
                      f"platform '{platform}' tidak dikenal", pilihan=list(PLATFORMS))

    registri = _rows("products.csv")
    baris = next((r for r in registri if r["sku"] == sku), None)
    if baris is None:
        return _gagal("sku_tidak_dikenal", f"SKU '{sku}' tidak ada di registri",
                      pilihan=[r["sku"] for r in registri])

    promo = (baris.get("harga_promo") or "").strip()
    produk = {
        "sku": baris["sku"],
        "nama": baris["nama_produk"],
        "kategori": baris.get("kategori", ""),
        "isi": baris.get("isi", ""),
        "harga": _rupiah(baris.get("harga")),
        "harga_promo": _rupiah(promo) if promo else None,
        "kuota_promo": (baris.get("kuota_promo") or "").strip() or None,
        "bpom": baris.get("notifikasi_bpom", ""),
        "status_halal": baris.get("cert_status", ""),
        "catatan": baris.get("catatan", ""),
    }

    sertifikat = [
        {
            "cert_id": s["cert_id"],
            "nomor": s["nomor"],
            "status": s["status"],
            "berlaku_sampai": s["berlaku_sampai"],
        }
        for s in _rows("certificates.csv")
        if sku in (s.get("sku_tercakup") or "").split("|")
    ]

    nomor = sku.split("-")[-1]
    lembar = sorted((DATA / "product_sheets").glob(f"PS-{nomor}_*.md"))
    lembar_teks = lembar[0].read_text(encoding="utf-8").strip() if lembar else ""

    briefs = sorted((DATA / "briefs").glob("*.md"))
    akhir_nama = baris["nama_produk"].split()[-1].lower()
    pilih = next((b for b in briefs if akhir_nama in b.name.lower()),
                 briefs[0] if briefs else None)

    batas = BATAS[platform]
    return {
        "ok": True,
        "sku": sku,
        "platform": platform,
        "produk": produk,
        "sertifikat": sertifikat,
        "sertifikat_catatan": (
            "Tidak ada sertifikat atas nama SKU ini. Jangan menaruh klaim halal di fakta_boleh."
            if not sertifikat else
            "Klaim halal hanya boleh memakai nomor yang statusnya AKTIF dan mencakup SKU ini."
        ),
        "lembar_produk": lembar_teks,
        "brief": pilih.read_text(encoding="utf-8").strip() if pilih else "",
        "spesifikasi_platform": (DATA / "platform_specs.md").read_text(encoding="utf-8").strip(),
        "nada_merek": (DATA / "brand_tone_guide.md").read_text(encoding="utf-8").strip(),
        "batas": {
            "kata_maks": batas["kata_maks"],
            "karakter_maks": batas["karakter_maks"],
            "emoji_maks": batas["emoji_maks"],
        },
        "catatan": "lembar_produk adalah SATU-SATUNYA sumber fakta. Brief tidak menambah fakta.",
    }


# --------------------------------------------------------------------------- 3. rulebook
# Lapis mana yang memeriksa tiap aturan. Semua punya pemeriksa deterministik;
# R-03, R-04, dan R-11 juga dibantu lapis-2 karena cakupan frasa tidak lengkap.
_LAYER = {
    "R-01": ["deterministik"], "R-02": ["deterministik"], "R-03": ["deterministik", "lapis-2"],
    "R-04": ["deterministik", "lapis-2"], "R-05": ["deterministik"], "R-06": ["deterministik"],
    "R-07": ["deterministik"], "R-08": ["deterministik"], "R-09": ["deterministik"],
    "R-10": ["deterministik"], "R-11": ["deterministik", "lapis-2"], "R-12": ["deterministik"],
    "R-13": ["deterministik"], "R-14": ["deterministik"], "R-15": ["deterministik"],
    "R-16": ["deterministik"], "R-17": ["deterministik"], "R-18": ["deterministik"],
    "R-19": ["deterministik"], "R-20": ["deterministik"], "R-21": ["deterministik"],
}


def get_rulebook(rule_ids: list[str] | None = None) -> dict:
    """Aturan R-01..R-21 beserta lapis pemeriksanya."""
    diminta = list(rule_ids) if rule_ids else sorted(RULEBOOK)
    aturan, tidak_dikenal = [], []
    for rid in diminta:
        if rid not in RULEBOOK:
            tidak_dikenal.append(rid)
            continue
        aturan.append({
            "rule_id": rid,
            "teks": RULEBOOK[rid],
            "lapis": _LAYER.get(rid, ["deterministik"]),
        })
    hasil = {"jumlah": len(aturan), "aturan": aturan}
    if tidak_dikenal:
        hasil["tidak_dikenal"] = tidak_dikenal
    return hasil


# --------------------------------------------------------------------------- 4. rencana
def plan_content(sku: str, platform: str, brief: str | None = None,
                 angle: str | None = None) -> dict:
    """Susun rencana tervalidasi. Tidak menulis satu kalimat marketing pun."""
    if platform not in PLATFORMS:
        return _gagal("platform_tidak_dikenal",
                      f"platform '{platform}' tidak dikenal", pilihan=list(PLATFORMS))
    if sku not in _PLANNER.products:
        return _gagal("sku_tidak_dikenal", f"SKU '{sku}' tidak ada di registri",
                      pilihan=sorted(_PLANNER.products))

    with _LOCK:
        asli = _PLANNER.brief
        if brief is not None:
            _PLANNER.brief = brief
        try:
            plan = _PLANNER(_PLANNER.brief, sku, platform)
        except (KeyError, ContractError) as e:
            return _gagal("rencana_gagal", str(e))
        finally:
            _PLANNER.brief = asli

        if angle:
            plan.angle = angle
            try:
                plan = _validate_plan(plan, "mcp-client")
            except ContractError as e:
                return {"ok": False, "valid": False, "masalah": e.masalah}

    return {"ok": True, "plan": plan.to_dict(), "batas": BATAS[platform],
            "mode": plan.mode}


# --------------------------------------------------------------------------- 5. validasi
def validate_plan(plan: dict) -> dict:
    """Validasi bentuk rencana sebelum masuk loop."""
    try:
        hasil = _validate_plan(plan, "mcp-client")
    except ContractError as e:
        return {"valid": False, "masalah": e.masalah}
    return {"valid": True, "masalah": [], "plan": hasil.to_dict()}


# --------------------------------------------------------------------------- 6. draf
def write_draft(plan, feedback: list[dict] | None = None, iteration: int = 1) -> dict:
    """Tulis draf dari rencana. `feedback` = temuan Reviewer pada iterasi sebelumnya."""
    try:
        obj = Plan.from_dict(plan, pembuat="mcp-client") if isinstance(plan, dict) else plan
    except ContractError as e:
        return _gagal("rencana_tidak_sah", str(e), masalah=e.masalah)
    if not isinstance(obj, Plan):
        return _gagal("rencana_tidak_sah", "plan harus objek JSON berbentuk Plan")

    masalah = obj.validate("mcp-client")
    if masalah:
        return _gagal("rencana_tidak_sah", "rencana tidak lolos validasi", masalah=masalah)

    it = _iterasi(iteration)
    with _LOCK:
        try:
            draf = _WRITER(obj, feedback or None, it)
        except (ContractError, KeyError) as e:
            return _gagal("draf_gagal", str(e))

    return {"ok": True, "iteration": it, "draft": draf,
            "kata": len(draf.split()), "karakter": len(draf)}


# --------------------------------------------------------------------------- 7. review
_ARTI = {
    "LOLOS": "Tidak ada pelanggaran yang ditemukan. Ini belum persetujuan publikasi.",
    "TOLAK": "Ada pelanggaran. Perbaiki temuan lalu kirim ulang sebagai iterasi berikutnya.",
    "PERLU_DATA": "Tidak ada pelanggaran terdeteksi, tetapi data produk tidak cukup "
                  "untuk memverifikasi. Ini BUKAN lulus.",
}


def review_draft(draft: str, sku: str, platform: str,
                 findings: list[dict] | None = None, iteration: int = 1,
                 write_audit: bool = False) -> dict:
    """Nilai draf. `findings` = temuan lapis-2 dari model pemanggil; kutipannya diverifikasi."""
    if not isinstance(draft, str) or not draft.strip():
        return _gagal("draf_kosong", "draft harus teks yang tidak kosong")
    if len(draft) > MAX_DRAFT:
        return _gagal("draf_terlalu_panjang", f"maks {MAX_DRAFT} karakter",
                      panjang=len(draft))
    if platform not in PLATFORMS:
        return _gagal("platform_tidak_dikenal",
                      f"platform '{platform}' tidak dikenal", pilihan=list(PLATFORMS))
    if findings is not None and not isinstance(findings, list):
        return _gagal("findings_tidak_sah", "findings harus daftar objek")
    if findings and len(findings) > MAX_FINDINGS:
        return _gagal("findings_terlalu_banyak", f"maks {MAX_FINDINGS} temuan",
                      jumlah=len(findings))

    it = _iterasi(iteration)
    with _LOCK:
        hasil = _REVIEWER.review(draft, sku, platform, it,
                                 llm_findings=findings or None,
                                 actor=ACTOR, log=bool(write_audit))

    return {
        "ok": True,
        "verdict": hasil.verdict,
        "artinya": _ARTI.get(hasil.verdict, ""),
        "sku": hasil.sku,
        "platform": hasil.platform,
        "iteration": hasil.iteration,
        "jumlah_temuan": len(hasil.violations),
        "temuan": [v.as_dict() for v in hasil.violations],
        "dibuang_llm": hasil.dropped_llm,
        "catatan": hasil.catatan,
        "pemeriksaan": hasil.checks,
    }


# --------------------------------------------------------------------------- 8. siklus
def run_cycle(sku: str, platform: str, brief: str | None = None) -> dict:
    """
    Planner → Writer → Reviewer, maksimal tiga iterasi.

    Sengaja TIDAK memanggil `ContentPipeline.run()`: fungsi itu menyetujui sendiri
    dengan approver hardcoded `EMP-014`. Lewat jaringan, itu persetujuan diri.
    Siklus ini berhenti di LOLOS dan menyerahkan approval ke manusia.
    """
    rencana = plan_content(sku, platform, brief)
    if not rencana.get("ok"):
        return rencana
    plan = rencana["plan"]

    draf_hasil = write_draft(plan)
    if not draf_hasil.get("ok"):
        return draf_hasil
    draf = draf_hasil["draft"]

    riwayat: list[dict] = []
    for it in range(1, MAX_ITERASI + 1):
        hasil = review_draft(draf, sku, platform, iteration=it, write_audit=True)
        if not hasil.get("ok"):
            return hasil
        riwayat.append({
            "iterasi": it,
            "verdict": hasil["verdict"],
            "jumlah_temuan": hasil["jumlah_temuan"],
            "aturan": sorted({t["rule_id"] for t in hasil["temuan"]}),
            "temuan": hasil["temuan"],
        })

        if hasil["verdict"] == "LOLOS":
            return {
                "ok": True, "status": "LOLOS", "iterasi": it,
                "konten_final": draf, "riwayat": riwayat, "plan": plan,
                "catatan": "Berhenti di LOLOS. Belum disetujui manusia. "
                           "Langkah berikutnya: request_approval lalu approve_publication.",
            }
        if hasil["verdict"] == "PERLU_DATA":
            return {
                "ok": True, "status": "PERLU_DATA", "iterasi": it,
                "konten_final": "", "riwayat": riwayat, "plan": plan,
                "catatan": "PERLU_DATA bukan lulus: data produk tidak cukup untuk memverifikasi.",
            }
        if it == MAX_ITERASI:
            break

        lanjut = write_draft(plan, feedback=hasil["temuan"], iteration=it + 1)
        if not lanjut.get("ok"):
            return lanjut
        draf = lanjut["draft"]

    return {
        "ok": True, "status": "ESKALASI", "iterasi": MAX_ITERASI,
        "konten_final": "", "riwayat": riwayat, "plan": plan,
        "catatan": "Tiga iterasi tercapai. Eskalasi ke manusia (Halal/Regulatory) "
                   "dengan riwayat revisi.",
    }


# --------------------------------------------------------------------------- 9-10. audit
def audit_verify() -> dict:
    """Telusuri rantai hash audit. Rusak berarti ada entri yang diubah atau dihapus."""
    with _LOCK:
        utuh, pesan, jumlah = _LOG.verify()
    return {"utuh": utuh, "pesan": pesan, "jumlah_entri": jumlah,
            "berkas": _LOG.path.name}


def audit_tail(n: int = 10) -> dict:
    """n entri audit terakhir, maksimal 100."""
    try:
        k = int(n)
    except (TypeError, ValueError):
        return _gagal("n_tidak_sah", "n harus bilangan bulat")
    k = max(1, min(k, MAX_AUDIT_TAIL))
    with _LOCK:
        entri = _LOG.tail(k)
    return {"diminta": n, "dikembalikan": len(entri),
            "maks": MAX_AUDIT_TAIL, "entri": entri}


# --------------------------------------------------------------------------- 11. usul
def request_approval(sku: str, platform: str, content: str) -> dict:
    """Ajukan konten ke gerbang. Hasilnya PROPOSED — belum disetujui siapa pun."""
    if not isinstance(content, str) or not content.strip():
        return _gagal("konten_kosong", "content harus teks yang tidak kosong")
    if len(content) > MAX_DRAFT:
        return _gagal("konten_terlalu_panjang", f"maks {MAX_DRAFT} karakter",
                      panjang=len(content))

    with _LOCK:
        plan = _GATE.propose(ACTOR, "publikasikan", {
            "sku": sku, "platform": platform, "konten": content,
        })

    return {
        "ok": True,
        "plan_id": plan["plan_id"],
        "status": plan["status"],
        "actor": plan["actor"],
        "action": plan["action"],
        "kedaluwarsa_menit": _GATE.ttl,
        "catatan": "PROPOSED. Belum disetujui. Manusia harus memanggil "
                   "approve_publication dengan plan_id ini dan kunci approval.",
    }


# --------------------------------------------------------------------------- 12. setujui
def approve_publication(plan_id: str, approval_key: str, note: str = "") -> dict:
    """
    Setujui satu plan. Nama approver DITURUNKAN dari kunci, bukan diklaim pemanggil.

    Kunci diperiksa lebih dulu supaya plan_id palsu tidak membocorkan plan mana
    yang ada. Kunci yang cocok menentukan siapa yang menyetujui; ApprovalGate
    tetap menolak bila nama itu sama dengan pemohon.
    """
    if not isinstance(approval_key, str) or not approval_key.strip():
        with _LOCK:
            _GATE.blocked("(tanpa kunci)", plan_id, "kunci approval kosong")
        return _gagal("approval_key_kosong", "approval_key wajib diisi")

    daftar, salah = _daftar_approver()
    if salah:
        with _LOCK:
            _GATE.blocked("(tidak dikenal)", plan_id, "registri approver bermasalah")
        return _gagal("approval_belum_dikonfigurasi", salah)
    if not daftar:
        with _LOCK:
            _GATE.blocked("(tidak dikenal)", plan_id, "kunci approval tidak dikonfigurasi")
        return _gagal("approval_belum_dikonfigurasi",
                      "Tidak ada kunci approver di server. Isi MCP_APPROVER_KEYS "
                      '(JSON {"Nama": "<sha256(kunci)>"}) atau MCP_APPROVAL_KEY + '
                      "MCP_APPROVAL_KEY_OWNER. Buat kuncinya: "
                      "python -m mcp_server.gen_approver_keys Nama")

    ringkas = _sha256(approval_key.strip())
    nama = next((n for n, h in daftar.items() if hmac.compare_digest(ringkas, h)), None)
    if nama is None:
        # Percobaan ini dicatat, tetapi kuncinya tidak pernah. Tanpa catatan,
        # tebakan kunci berulang tidak meninggalkan jejak di rantai audit.
        with _LOCK:
            _GATE.blocked("(tidak dikenal)", plan_id, "kunci approval tidak cocok")
        return _gagal("approval_key_salah",
                      "kunci approval tidak cocok dengan approver mana pun")

    with _LOCK:
        try:
            plan = _GATE.approve(plan_id, nama, note or "")
        except KeyError:
            return _gagal("plan_tidak_ada",
                          f"plan {plan_id} tidak ada — salah id, atau server sudah restart")
        except PermissionError as e:
            return _gagal("approval_ditolak", str(e))

    return {
        "ok": True,
        "plan_id": plan["plan_id"],
        "status": plan["status"],
        "approver": plan["approver"],
        "catatan": "APPROVED. Tidak ada tool publikasi di server ini; rantai berhenti di sini.",
    }
