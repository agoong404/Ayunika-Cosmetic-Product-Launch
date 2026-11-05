"""
governance.py — lapisan akuntabilitas: audit log, gerbang approval, validator jawaban.

Tiga mekanisme yang menjawab tiga dari lima aturan handbook:

  Aturan 1 (menunjukkan sumber)  -> validate_answer(): draf tanpa blok SUMBER ditolak
  Aturan 3 (bertanya sebelum bertindak) -> ApprovalGate: aksi menolak tanpa plan APPROVED
  Aturan 5 (menyimpan catatan)   -> AuditLog: append-only + hash chain (tamper-evident)

Aturan 2 (batas izin) ada di `HalalEngine.can_read()`.
Aturan 4 (mengakui keterbatasan) ada di model status 4-nilai di `halal_engine.py`.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

TZ = timezone(timedelta(hours=7))
# Bisa dialihkan lewat env supaya uji otomatis tidak mengotori log sesi manual.
LOG_PATH = Path(os.environ.get("HALAL_AUDIT_DIR",
                               Path(__file__).resolve().parent / ".audit")) / "audit.jsonl"


def _now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- 5. catatan
class AuditLog:
    """
    Log append-only dengan hash chain.

    Setiap entri memuat hash entri sebelumnya. Mengubah atau menghapus satu baris akan
    memutus rantai dan terdeteksi oleh verify(). Ini alasan konkret kenapa "log" di sini
    bukan sekadar file teks.
    """

    def __init__(self, path: Path = LOG_PATH):
        self.path = path
        self.path.parent.mkdir(exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        # Cache entri terakhir: tanpa ini setiap append membaca ulang seluruh berkas,
        # sehingga biayanya tumbuh kuadratik (700 run -> ~9 juta baris dibaca).
        # Catatan: AuditLog mengasumsikan SATU penulis. verify() tetap membaca
        # seluruh berkas, jadi deteksi perubahan tidak terpengaruh cache ini.
        self._cache: tuple[int, str] | None = None

    def _last(self) -> tuple[int, str]:
        if self._cache is not None:
            return self._cache
        seq, h = 0, "0" * 64
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                seq, h = e["seq"], e["hash"]
        self._cache = (seq, h)
        return self._cache

    def append(self, actor: str, action: str, target: str = "",
               result: str = "", evidence: list[str] | None = None,
               meta: dict | None = None) -> dict:
        seq, prev = self._last()
        entry = {
            "seq": seq + 1,
            "ts": _now(),
            "actor": actor,
            "action": action,
            "target": target,
            "result": result,
            "evidence": evidence or [],
            "meta": meta or {},
            "prev": prev,
        }
        entry["hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._cache = (entry["seq"], entry["hash"])
        return entry

    def verify(self) -> tuple[bool, str, int]:
        """Telusuri rantai. Mengembalikan (utuh, pesan, jumlah entri)."""
        prev, n = "0" * 64, 0
        with open(self.path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                n += 1
                body = {k: v for k, v in e.items() if k != "hash"}
                calc = hashlib.sha256(
                    json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
                if e.get("hash") != calc:
                    return False, f"entri #{i} (seq {e.get('seq')}) isinya diubah", n
                if e.get("prev") != prev:
                    return False, f"rantai putus di entri #{i} (seq {e.get('seq')})", n
                prev = e["hash"]
        return True, "rantai utuh", n

    def tail(self, n: int = 10) -> list[dict]:
        lines = [l for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return [json.loads(l) for l in lines[-n:]]


# --------------------------------------------------------------------------- 3. approval
class ApprovalGate:
    """
    Gerbang aksi: tidak ada aksi keluar tanpa plan berstatus APPROVED.

    Aturan yang ditegakkan:
      - aksi menolak plan yang tidak ada / belum disetujui / sudah dipakai / kedaluwarsa
      - approver tidak boleh sama dengan pemohon (pemisahan tugas)
      - token sekali pakai (mencegah replay)
      - setiap transisi ditulis ke audit log
    """

    def __init__(self, log: AuditLog, ttl_minutes: int = 30):
        self.log = log
        self.ttl = ttl_minutes
        self.plans: dict[str, dict] = {}

    def propose(self, actor: str, action: str, payload: dict) -> dict:
        pid = "PLAN-" + secrets.token_hex(4).upper()
        self.plans[pid] = {
            "plan_id": pid, "actor": actor, "action": action, "payload": payload,
            "status": "PROPOSED", "created": time.time(), "approver": None, "used": False,
        }
        self.log.append(actor, "plan_propose", pid, "PROPOSED",
                        meta={"action": action, "payload": payload})
        return self.plans[pid]

    @staticmethod
    def _nama_aman(nama: str) -> str:
        """Batasi nama dari pemanggil supaya tidak bisa menyuntik isi log."""
        teks = " ".join(str(nama or "").split())
        return teks[:120] or "(kosong)"

    def blocked(self, actor: str, plan_id: str, reason: str, **extra) -> dict:
        """
        Catat percobaan yang ditolak.

        Tanpa ini, tebakan kunci approval tidak meninggalkan jejak apa pun: pemanggil
        bisa mencoba ribuan kunci dan rantai audit tetap terlihat bersih. Nama pelaku
        berasal dari pemanggil, jadi dipangkas dan dibatasi panjangnya.
        """
        meta = {"alasan": reason}
        meta.update(extra)
        return self.log.append(self._nama_aman(actor), "approval_blocked",
                               str(plan_id)[:64], "REFUSED", meta=meta)

    def approve(self, plan_id: str, approver: str, note: str = "") -> dict:
        p = self.plans.get(plan_id)
        if not p:
            self.blocked(approver, plan_id, "plan tidak ada")
            raise KeyError(f"plan {plan_id} tidak ada")
        if p["status"] != "PROPOSED":
            self.blocked(approver, plan_id, f"status {p['status']}")
            raise PermissionError(f"plan {plan_id} berstatus {p['status']}, bukan PROPOSED")
        if approver == p["actor"]:
            self.blocked(approver, plan_id,
                         "pemohon tidak boleh menyetujui aksinya sendiri",
                         pemohon=p["actor"])
            raise PermissionError("pemohon tidak boleh menyetujui aksinya sendiri")
        p.update(status="APPROVED", approver=approver, note=note, approved_at=time.time())
        self.log.append(approver, "plan_approve", plan_id, "APPROVED",
                        meta={"action": p["action"], "note": note})
        return p

    def reject(self, plan_id: str, approver: str, note: str = "") -> dict:
        p = self.plans.get(plan_id)
        if not p:
            raise KeyError(f"plan {plan_id} tidak ada")
        p.update(status="REJECTED", approver=approver, note=note)
        self.log.append(approver, "plan_reject", plan_id, "REJECTED", meta={"note": note})
        return p

    def execute(self, plan_id: str, executor: str, fn=None):
        """Jalankan aksi hanya bila plan APPROVED, belum dipakai, dan belum kedaluwarsa."""
        p = self.plans.get(plan_id)
        if not p:
            self.log.append(executor, "execute_blocked", plan_id, "REFUSED",
                            meta={"alasan": "plan tidak ada"})
            raise PermissionError("DITOLAK: plan tidak ada — aksi tidak dijalankan")

        if p["status"] != "APPROVED":
            self.log.append(executor, "execute_blocked", plan_id, "REFUSED",
                            meta={"alasan": f"status {p['status']}"})
            raise PermissionError(
                f"DITOLAK: plan berstatus {p['status']} — aksi tidak dijalankan")

        if p["used"]:
            self.log.append(executor, "execute_blocked", plan_id, "REFUSED",
                            meta={"alasan": "token sudah dipakai"})
            raise PermissionError("DITOLAK: token sudah dipakai — aksi tidak dijalankan")

        if time.time() - p["approved_at"] > self.ttl * 60:
            p["status"] = "EXPIRED"
            self.log.append(executor, "execute_blocked", plan_id, "REFUSED",
                            meta={"alasan": "token kedaluwarsa"})
            raise PermissionError("DITOLAK: token kedaluwarsa — aksi tidak dijalankan")

        p["used"] = True
        out = fn(p["payload"]) if fn else None
        self.log.append(executor, "execute", plan_id, "DONE",
                        meta={"action": p["action"], "approver": p["approver"]})
        return out


# --------------------------------------------------------------------------- 1. sumber
STATUS_TOKENS = ("HALAL_TERVERIFIKASI", "BELUM_TERVERIFIKASI",
                 "TIDAK_HALAL", "TIDAK_DITEMUKAN")


def validate_answer(text: str, evidence_ids: list[str]) -> dict:
    """
    Kontrak jawaban. Draf yang tidak memenuhi ini harus DITOLAK sistem, bukan diserahkan
    ke pengguna.

    Syarat:
      1. memuat tepat satu token status
      2. memuat blok SUMBER
      3. blok SUMBER menyebut minimal satu bukti yang benar-benar dipakai
      4. tidak memuat frasa klaim terlarang (L-02, L-03)
    """
    masalah = []

    found = [s for s in STATUS_TOKENS if s in text]
    if not found:
        masalah.append("tidak ada token status")
    elif len(found) > 1:
        masalah.append(f"status ambigu: {found}")

    if "SUMBER" not in text.upper():
        masalah.append("tidak ada blok SUMBER")
    else:
        if evidence_ids and not any(e in text for e in evidence_ids):
            masalah.append("blok SUMBER tidak menyebut bukti yang dipakai")

    import re as _re
    for pat, why in [(r"100\s*%\s*halal", "klaim superlatif (L-02)"),
                     (r"\bmui\b|lppom", "penerbit salah, harus BPJPH (L-03)"),
                     (r"dijamin\s+halal", "klaim jaminan (L-02)")]:
        if _re.search(pat, text.lower()):
            masalah.append(why)

    return {"lolos": not masalah, "masalah": masalah}


# --------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    import sys

    log = AuditLog()
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        ok, msg, n = log.verify()
        print(f"{'UTUH' if ok else 'RUSAK'}: {msg} ({n} entri)")
        print(f"berkas: {log.path}")
    elif len(sys.argv) > 1 and sys.argv[1] == "tail":
        for e in log.tail(int(sys.argv[2]) if len(sys.argv) > 2 else 10):
            print(f"#{e['seq']:3d} {e['ts'][11:19]} {e['actor']:8s} {e['action']:16s} "
                  f"{e['target']:12s} {e['result']}")
    else:
        print("pakai: python governance.py verify | tail [n]")
