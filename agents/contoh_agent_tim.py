"""
contoh_agent_tim.py — cetakan untuk agent buatan rekan tim.

Berkas ini sengaja dibuat sesederhana mungkin: dua fungsi, tanpa kelas, tanpa
framework. Kalau agent timmu lebih rumit (memanggil model, memakai tool, dsb),
bentuk luarnya tetap sama.

Cara memakai:

    TEAM_AGENTS_MODULE=agents.contoh_agent_tim python -m agents.harness --agents team

Yang WAJIB dipenuhi:

    planner(brief, sku, platform) -> Plan | dict
    writer(plan, feedback, iterasi) -> str

`feedback` berisi daftar temuan Reviewer (bisa None pada iterasi 1). Bentuknya:
    [{"rule_id": "R-07", "span": "...", "reason": "...", "fix": "...", "layer": "..."}]

Yang TIDAK boleh dilakukan Writer:
    · menambah fakta di luar plan.fakta_boleh
    · menyinggung halal kecuali ada di plan.fakta_boleh beserta nomornya
    · mengembalikan JSON, penjelasan, atau front-matter — kirim teks konten saja
"""
from __future__ import annotations

from agents.contract import Plan


def planner(brief: str, sku: str, platform: str) -> Plan:
    """
    Ganti isi fungsi ini dengan logika timmu.

    Minimal: kembalikan Plan yang berisi fakta boleh dan harga. Kalau ragu soal
    bentuknya, bangun Plan seperti contoh di bawah — sisanya sudah divalidasi
    otomatis sebelum masuk pipeline.
    """
    # Contoh paling minimal: delegasikan ke Planner bawaan supaya jalur team
    # bisa diuji lebih dulu, lalu ganti sedikit demi sedikit.
    from agents.planner import PlannerAgent

    ag = PlannerAgent()
    return ag(ag.brief, sku, platform)


def writer(plan: Plan, feedback: list[dict] | None = None, iterasi: int = 1) -> str:
    """
    Ganti isi fungsi ini dengan Writer timmu.

    Perhatikan: `plan` tidak memuat rulebook. Itu disengaja — Writer tidak boleh
    menjadi pengawas kepatuhannya sendiri. Yang kamu punya hanya fakta boleh,
    fakta dilarang, nada, dan catatan Reviewer.
    """
    from agents.writer import WriterAgent

    return WriterAgent()(plan, feedback, iterasi)
