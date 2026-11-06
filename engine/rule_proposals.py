"""
rule_proposals.py — suntingan manusia → usulan aturan baru (C-18).

Alurnya sengaja dua langkah dan berhenti di manusia:
    suntingan manusia  →  USULAN (PROPOSED, tersimpan di audit chain)
    kunci approver     →  DISETUJUI (APPROVED)
    TIDAK ADA langkah "aturan langsung aktif".

Mengapa tidak langsung aktif: aturan yang menolak konten adalah keputusan
regulatory. Menyuntikkannya otomatis dari satu suntingan berarti model bisa
mengubah batas kepatuhannya sendiri. Usulan yang disetujui hanya boleh
digabungkan ke `rulebook_claims.md` oleh manusia lewat tinjauan kode.
Modul ini sengaja TIDAK menulis ke reviewer.RULEBOOK.

Penyimpanan memakai AuditLog yang sama dengan governance.py, jadi setiap
usulan, persetujuan, dan penolakan masuk rantai hash yang bisa diverifikasi.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
USULAN_PATH = Path(os.environ.get("LOLOS_PROPOSALS_DIR", str(BASE / "engine" / ".audit"))) / "rule_proposals.json"

JENIS_SAH = {"frasa_dilarang", "klaim_wajib", "batas_platform", "klarifikasi"}
STATUS = ("PROPOSED", "APPROVED", "REJECTED", "MERGED")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s))).strip().lower()


def _kata(s: str) -> list[str]:
    return re.findall(r"[\w']+", _norm(s), re.UNICODE)


@dataclass
class Usulan:
    id: str
    sku: str
    jenis: str
    pola: str
    alasan: str
    kutipan_asli: str
    kutipan_suntingan: str
    status: str = "PROPOSED"
    dibuat: float = 0.0
    pemohon: str = "workbuddy-agent"
    approver: str = ""
    catatan: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id, "sku": self.sku, "jenis": self.jenis, "pola": self.pola,
            "alasan": self.alasan, "kutipan_asli": self.kutipan_asli,
            "kutipan_suntingan": self.kutipan_suntingan, "status": self.status,
            "dibuat": self.dibuat, "pemohon": self.pemohon,
            "approver": self.approver, "catatan": self.catatan,
        }


# ------------------------------------------------------------------ penyimpanan
def _muat() -> list[dict]:
    if not USULAN_PATH.exists():
        return []
    try:
        return json.loads(USULAN_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _simpan(rows: list[dict]) -> None:
    USULAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    USULAN_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _audit():
    """AuditLog dipakai bila tersedia; uji bisa memindahkannya via HALAL_AUDIT_DIR."""
    import sys
    if str(BASE / "engine") not in sys.path:
        sys.path.insert(0, str(BASE / "engine"))
    from governance import AuditLog  # noqa: E402
    return AuditLog()


# ------------------------------------------------------------------ diff
def _bedah(asli: str, suntingan: str) -> tuple[list[str], list[str]]:
    """Kata yang dihapus dan ditambahkan manusia, dengan urutan dijaga."""
    from difflib import SequenceMatcher
    a, b = _kata(asli), _kata(suntingan)
    dihapus, ditambah = [], []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b).get_opcodes():
        if tag in ("replace", "delete"):
            dihapus.extend(a[i1:i2])
        if tag in ("replace", "insert"):
            ditambah.extend(b[j1:j2])
    return dihapus, ditambah


def buat_usulan(sku: str, asli: str, suntingan: str, jenis: str,
                alasan: str = "", pemohon: str = "workbuddy-agent") -> dict:
    """
    Ubah satu suntingan manusia menjadi usulan aturan berstatus PROPOSED.

    `pola` diambil dari bagian teks yang dihapus (untuk frasa terlarang) atau
    ditambahkan (untuk klaim wajib). Tidak ada aturan yang dijalankan di sini.
    """
    if jenis not in JENIS_SAH:
        return {"ok": False, "error": "jenis_tidak_sah",
                "pesan": f"jenis harus salah satu dari {', '.join(sorted(JENIS_SAH))}"}
    if not _norm(asli) or not _norm(suntingan):
        return {"ok": False, "error": "teks_kosong", "pesan": "Draf asli dan suntingan wajib diisi."}
    if _norm(asli) == _norm(suntingan):
        return {"ok": False, "error": "tidak_ada_perubahan",
                "pesan": "Tidak ada perubahan; tidak ada usulan yang bisa diturunkan."}

    dihapus, ditambah = _bedah(asli, suntingan)
    if jenis == "frasa_dilarang":
        dasar = dihapus
    else:
        dasar = ditambah or dihapus
    pola = " ".join(dasar[:12]).strip()
    if not pola:
        return {"ok": False, "error": "pola_tidak_terbentuk",
                "pesan": "Suntingan hanya mengubah tanda baca/urutan; tidak ada kandidat aturan."}

    cap = time.time()
    uid = "R-USUL-" + hashlib.sha256(
        f"{sku}|{jenis}|{_norm(pola)}|{_norm(asli)}|{cap}".encode("utf-8")
    ).hexdigest()[:10].upper()
    u = Usulan(id=uid, sku=sku, jenis=jenis, pola=pola,
               alasan=alasan or "Diturunkan dari suntingan manusia.",
               kutipan_asli=asli.strip()[:2000], kutipan_suntingan=suntingan.strip()[:2000],
               dibuat=cap, pemohon=pemohon)

    rows = _muat()
    rows.append(u.as_dict())
    _simpan(rows)
    try:
        _audit().append(pemohon, "rule_propose", uid, "PROPOSED",
                        meta={"sku": sku, "jenis": jenis, "pola": pola})
    except Exception:
        pass
    return {"ok": True, "usulan": u.as_dict(),
            "catatan": "Berstatus PROPOSED. Butuh kunci approver; tidak pernah aktif otomatis.",
            "langkah_berikutnya": "Manusia meninjau, lalu setujui dengan approve_proposal()."}


def daftar(status: str | None = None) -> list[dict]:
    rows = _muat()
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows


def _approver_dari_kunci(kunci: str) -> str | None:
    """Nama approver diturunkan dari sha256 kunci, bukan diklaim pemanggil."""
    import hmac
    mentah = os.environ.get("MCP_APPROVER_KEYS", "").strip()
    if not mentah:
        p = BASE / ".approver_keys"
        if p.exists():
            mentah = p.read_text(encoding="utf-8").strip()
    if not mentah:
        return None
    try:
        reg = json.loads(mentah)
    except json.JSONDecodeError:
        return None
    ringkas = hashlib.sha256(kunci.strip().encode("utf-8")).hexdigest()
    return next((n for n, h in reg.items() if hmac.compare_digest(ringkas, str(h))), None)


def setujui(usulan_id: str, kunci: str, catatan: str = "") -> dict:
    """Setujui usulan. Status APPROVED — tetap TIDAK mengubah RULEBOOK."""
    approver = _approver_dari_kunci(kunci)
    if not approver:
        try:
            _audit().append("(tidak dikenal)", "rule_approve_blocked", usulan_id, "REFUSED",
                            meta={"alasan": "kunci approval tidak cocok"})
        except Exception:
            pass
        return {"ok": False, "error": "kunci_approval_salah",
                "pesan": "Kunci tidak cocok dengan approver mana pun. Kunci tidak pernah disimpan."}

    rows = _muat()
    untuk = next((r for r in rows if r.get("id") == usulan_id), None)
    if not untuk:
        return {"ok": False, "error": "usulan_tidak_ada", "pesan": f"{usulan_id} tidak ditemukan."}
    if untuk["status"] != "PROPOSED":
        return {"ok": False, "error": "status_salah",
                "pesan": f"Usulan berstatus {untuk['status']}, bukan PROPOSED."}
    if approver == untuk.get("pemohon"):
        return {"ok": False, "error": "self_approval",
                "pesan": "Pemohon tidak boleh menyetujui usulannya sendiri."}

    untuk.update(status="APPROVED", approver=approver, catatan=catatan)
    _simpan(rows)
    try:
        _audit().append(approver, "rule_approve", usulan_id, "APPROVED",
                        meta={"jenis": untuk["jenis"], "pola": untuk["pola"]})
    except Exception:
        pass
    return {"ok": True, "usulan": untuk,
            "catatan": "APPROVED, tetapi BELUM aktif. Penggabungan ke rulebook_claims.md "
                       "harus dilakukan manusia lewat tinjauan kode; tidak ada auto-apply."}


def tolak(usulan_id: str, kunci: str, alasan: str = "") -> dict:
    approver = _approver_dari_kunci(kunci)
    if not approver:
        return {"ok": False, "error": "kunci_approval_salah", "pesan": "Kunci tidak cocok."}
    rows = _muat()
    untuk = next((r for r in rows if r.get("id") == usulan_id), None)
    if not untuk:
        return {"ok": False, "error": "usulan_tidak_ada", "pesan": f"{usulan_id} tidak ditemukan."}
    untuk.update(status="REJECTED", approver=approver, catatan=alasan)
    _simpan(rows)
    try:
        _audit().append(approver, "rule_reject", usulan_id, "REJECTED", meta={"alasan": alasan})
    except Exception:
        pass
    return {"ok": True, "usulan": untuk}


def ekspor_markdown(status: str = "APPROVED") -> str:
    """Bahan tinjauan manusia. Tidak ditulis ke berkas rulebook mana pun."""
    baris = ["# Usulan aturan untuk ditinjau manusia", "",
             "> Dihasilkan `engine/rule_proposals.py`. Menggabungkan ke rulebook adalah",
             "> keputusan manusia, bukan aksi otomatis.", ""]
    rows = [r for r in _muat() if r.get("status") == status]
    if not rows:
        baris.append("_Belum ada usulan berstatus ini._")
    for r in rows:
        baris += [f"## {r['id']} · {r['jenis']} · {r['sku']}",
                  f"- **Pola:** `{r['pola']}`",
                  f"- **Alasan:** {r['alasan']}",
                  f"- **Disetujui:** {r.get('approver') or '-'}",
                  f"- **Draf asli:** {r['kutipan_asli'][:160]}",
                  f"- **Suntingan:** {r['kutipan_suntingan'][:160]}", ""]
    return "\n".join(baris)
