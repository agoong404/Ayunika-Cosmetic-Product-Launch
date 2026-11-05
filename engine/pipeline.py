"""
pipeline.py — orkestrator Challenge C: Planner → Writer → Reviewer → (loop) → Approval → Publish.

Yang sudah jadi di sini:
  - kendali loop (maks 3 iterasi, lalu eskalasi)
  - gerbang approval untuk publikasi (tidak ada yang terbit tanpa plan APPROVED)
  - log setiap tahap ke audit chain

Yang perlu diganti tim:
  - `TemplatePlanner` dan `ScriptedWriter` di bawah hanyalah pengganti sementara.
    Ganti dengan agent Planner/Writer milikmu — kontraknya cukup:
        planner(brief, sku, platform) -> dict rencana
        writer(plan, feedback, iterasi) -> str draf
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from governance import AuditLog, ApprovalGate
from reviewer import Reviewer, ReviewResult, strip_markdown

DATA = Path(__file__).resolve().parent.parent / "dataset_c"


# --------------------------------------------------------------------------- peran
class TemplatePlanner:
    """Pengganti Planner. Cukup mengembalikan struktur yang bisa dibaca Writer."""

    def __call__(self, brief: str, sku: str, platform: str) -> dict:
        fakta = re.findall(r"^\d+\.\s+\"(.+?)\"\s*(✅|❌)?", brief, re.M)
        return {
            "sku": sku,
            "platform": platform,
            "struktur": ["HOOK", "ISI", "CTA"] if platform == "tiktok" else ["baris pembuka", "isi", "CTA"],
            "fakta_boleh": [f for f, ok in fakta if ok == "✅"],
            "fakta_dilarang": [f for f, ok in fakta if ok == "❌"],
        }


class ScriptedWriter:
    """
    Pengganti Writer: mengembalikan draf v1 → v2 → v3 sesuai urutan iterasi.
    Dipakai supaya pipeline bisa didemokan tanpa Writer Agent sungguhan.
    """

    def __init__(self, paths: list[Path]):
        self.drafts = []
        for p in paths:
            t = p.read_text(encoding="utf-8")
            t = re.sub(r"^---.*?---", "", t, flags=re.S)
            self.drafts.append(strip_markdown(t))

    def __call__(self, plan: dict, feedback: list | None, iteration: int) -> str:
        idx = min(iteration - 1, len(self.drafts) - 1)
        return self.drafts[idx]


# --------------------------------------------------------------------------- hasil
@dataclass
class PipelineResult:
    sku: str
    platform: str
    status: str                      # TERBIT | ESKALASI | GAGAL
    iterasi: int = 0
    riwayat: list[dict] = field(default_factory=list)
    konten_final: str = ""
    plan_id: str = ""
    mode_planner: str = ""           # deterministik | llm | fallback
    error: str = ""                  # terisi bila ada tahap yang gagal

    def ringkas(self) -> str:
        baris = [f"{self.sku}/{self.platform} → {self.status} setelah {self.iterasi} iterasi"]
        for h in self.riwayat:
            baris.append(f"  iterasi {h['iterasi']}: {h['verdict']} · "
                         f"{h['jumlah_temuan']} temuan {h['aturan'] or ''}")
        if self.plan_id:
            baris.append(f"  plan: {self.plan_id}")
        if self.error:
            baris.append(f"  error: {self.error}")
        return "\n".join(baris)


# --------------------------------------------------------------------------- pipeline
class ContentPipeline:
    MAX_ITERASI = 3

    def __init__(self, reviewer: Reviewer | None = None,
                 log: AuditLog | None = None, gate: ApprovalGate | None = None,
                 llm=None):
        self.log = log or AuditLog()
        self.reviewer = reviewer or Reviewer(audit=self.log)
        self.gate = gate or ApprovalGate(self.log)
        # Lapis-2 hanya aktif bila ada model. Tanpa model, perilaku persis seperti
        # sebelumnya — bukan "dianggap aman", tapi "tidak ada penilaian tambahan".
        self.layer2 = None
        if llm is not None:
            from layer2 import Layer2
            self.layer2 = Layer2(llm=llm, reviewer=self.reviewer)

    def run(self, brief: str, sku: str, platform: str,
            planner=None, writer=None,
            approver: str = "EMP-014", actor: str = "orchestrator") -> PipelineResult:
        planner = planner or TemplatePlanner()
        if writer is None:
            writer = ScriptedWriter(sorted((DATA / "sample_drafts").glob("DRAFT-101_v*.md")))

        res = PipelineResult(sku, platform, status="BERJALAN")

        # 1. PLANNER — kegagalan di sini menghentikan kampanye, bukan dilempar ke atas.
        try:
            plan = planner(brief, sku, platform)
        except Exception as e:                      # noqa: BLE001 — semua kegagalan agent harus tercatat
            return self._gagal(res, "planner", e)

        rencana = plan if isinstance(plan, dict) else getattr(plan, "__dict__", {})
        res.mode_planner = str(rencana.get("mode", "") or "")
        self.log.append(actor, "plan", f"{sku}/{platform}", "OK",
                        meta={"struktur": rencana.get("struktur"),
                              "mode": res.mode_planner,
                              "fakta_dilarang": len(rencana.get("fakta_dilarang", []) or [])})

        feedback = None
        for it in range(1, self.MAX_ITERASI + 1):
            res.iterasi = it

            # 2. WRITER — exception tidak boleh lolos: tanpa draf, tidak ada yang dinilai,
            #    dan yang tidak dinilai tidak boleh diterbitkan.
            try:
                draft = writer(plan, feedback, it)
            except Exception as e:                  # noqa: BLE001
                return self._gagal(res, "writer", e)
            if not isinstance(draft, str) or not draft.strip():
                return self._gagal(res, "writer",
                                   ValueError(f"draf kosong / bukan teks ({type(draft).__name__})"))

            self.log.append("writer-agent", "write", f"{sku}/{platform}", "DRAFT",
                            meta={"iterasi": it, "panjang": len(draft)})

            # 3a. REVIEWER LAPIS-2 (bila ada model) — menilai yang tidak bisa dicek kode
            l2 = None
            if self.layer2 is not None:
                l2 = self.layer2.run(draft, sku, platform)
                if l2["error"]:
                    # Gagal menilai bukan alasan meloloskan. Dicatat, lalu review
                    # berjalan hanya dengan lapis-1 — dan itu terlihat di log.
                    self.log.append("reviewer-agent", "layer2_error", f"{sku}/{platform}",
                                    "GAGAL", meta={"error": l2["error"]})
                elif l2["mentah"] or l2["dibuang"]:
                    self.log.append("reviewer-agent", "layer2", f"{sku}/{platform}", "OK",
                                    meta={"mentah": l2["mentah"],
                                          "diterima": len(l2["diterima"]),
                                          "dibuang": len(l2["dibuang"])})

            # 3b. REVIEWER — lapis-1 selalu jalan; lapis-2 digabung bila ada temuannya
            try:
                review = self.reviewer.review(
                    draft, sku, platform, it,
                    llm_findings=(l2["diterima"] if l2 and l2["diterima"] else None))
            except Exception as e:                  # noqa: BLE001
                return self._gagal(res, "reviewer", e)

            res.riwayat.append({
                "iterasi": it, "verdict": review.verdict,
                "jumlah_temuan": len(review.violations),
                "aturan": sorted({v.rule_id for v in review.violations}),
                "lapis2": (None if not l2 else
                           {"mentah": l2["mentah"], "diterima": len(l2["diterima"]),
                            "dibuang": len(l2["dibuang"]), "error": l2["error"]}),
            })

            decision = self.reviewer.decide_next(review)

            if decision["aksi"] == "SELESAI":
                res.konten_final = draft
                break
            if decision["aksi"] == "ESKALASI":
                res.status = "ESKALASI"
                self.log.append(actor, "escalate", f"{sku}/{platform}", "ESKALASI",
                                meta={"sisa": decision["sisa_masalah"]})
                return res

            feedback = [v.as_dict() for v in review.violations]

        if not res.konten_final:
            res.status = "ESKALASI"
            self.log.append(actor, "escalate", f"{sku}/{platform}", "ESKALASI",
                            meta={"alasan": "loop selesai tanpa konten yang lolos"})
            return res

        # 4. APPROVAL MANUSIA (tidak ada publikasi tanpa ini)
        plan_obj = self.gate.propose(actor, "publikasikan",
                                     {"sku": sku, "platform": platform,
                                      "konten": res.konten_final})
        res.plan_id = plan_obj["plan_id"]
        self.gate.approve(res.plan_id, approver, "konten lolos review")
        self.gate.execute(res.plan_id, actor, lambda p: None)
        res.status = "TERBIT"
        return res

    def _gagal(self, res: PipelineResult, tahap: str, err: Exception) -> PipelineResult:
        """Satu pintu untuk semua kegagalan agent: status GAGAL, tercatat, tidak terbit."""
        res.status = "GAGAL"
        res.error = f"{tahap}: {type(err).__name__}: {err}"
        res.konten_final = ""
        self.log.append("orchestrator", "agent_error", f"{res.sku}/{res.platform}", "GAGAL",
                        meta={"tahap": tahap, "error": res.error})
        return res


# --------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    brief = (DATA / "briefs" / "BRF-101_launch_bright_serum.md").read_text(encoding="utf-8")
    p = ContentPipeline()
    out = p.run(brief, "AY-SR-101", "tiktok")
    print(out.ringkas())
    print("\n--- konten final ---")
    print(out.konten_final.strip()[:400])
