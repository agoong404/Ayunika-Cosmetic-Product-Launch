"""
test_wiring.py — membuktikan jalur LLM benar-benar tersambung, tanpa perlu API key.

Kenapa ada berkas ini: kode yang "seharusnya jalan" dan kode yang "terbukti jalan"
adalah dua hal berbeda. Dengan klien palsu, seluruh jalur model bisa diuji hari ini:
apakah JSON model dipakai, apakah kegagalan model jatuh ke deterministik, dan
apakah budget panggilan benar-benar menghentikan loop.

Yang TIDAK diuji di sini: kualitas keluaran model sungguhan. Itu hanya bisa dinilai
setelah kamu memasang API key dan menjalankan 5 draf nyata.

    python -m agents.test_wiring
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

import os
import tempfile

os.environ.setdefault("HALAL_AUDIT_DIR", str(Path(tempfile.gettempdir()) / "halal_wiring_audit"))

from agents.llm.client import LLMBudgetError, LLMClient, LLMConfig, LLMError  # noqa: E402
from agents.planner import PlannerAgent                                        # noqa: E402
from agents.writer import WriterAgent                                          # noqa: E402
from governance import ApprovalGate, AuditLog                                  # noqa: E402
from pipeline import ContentPipeline                                           # noqa: E402
from reviewer import Reviewer                                                  # noqa: E402

BRIEF = (ROOT / "dataset_c" / "briefs" / "BRF-101_launch_bright_serum.md").read_text(encoding="utf-8")
baris: list[tuple[str, str, bool, str]] = []


def cek(kode: str, nama: str, ok: bool, detail: str = "") -> None:
    baris.append((kode, nama, bool(ok), detail))


# --------------------------------------------------------------------------- klien palsu
PLAN_JSON = {
    "sku": "AY-SR-101",
    "platform": "tiktok",
    "angle": "Bahan aktif yang dijelaskan apa adanya.",
    "struktur": ["HOOK", "ISI", "CTA"],
    "fakta_boleh": ["Mengandung niacinamide 5% dan vitamin C 10%.",
                    "Tekstur ringan, cepat meresap."],
    "fakta_dilarang": ["klaim halal", "janji hasil"],
    "harga": "Rp149.000",
    "harga_promo": "Rp129.000",
    "bpom": "NA18241300123",
    "isi": "30 ml",
    "disclaimer": "Hasil dapat berbeda pada setiap orang.",
    "emoji_maks": 2,
    "catatan": "jangan menyinggung halal",
}

DRAF_LLM = (
    "HOOK (0–3 dtk)\n"
    "Merawat kulit nggak perlu janji berlebihan.\n\n"
    "ISI (3–45 dtk)\n"
    "Mengandung niacinamide 5% dan vitamin C 10%. Teksturnya ringan dan cepat meresap.\n\n"
    "CTA (45–60 dtk)\n"
    "Promo peluncuran Rp129.000 untuk 100 pembeli pertama, dari harga normal Rp149.000.\n\n"
    "Hasil dapat berbeda pada setiap orang."
)


class FakeLLM:
    """Meniru antarmuka LLMClient tanpa jaringan."""

    def __init__(self, gagal: bool = False):
        self.gagal = gagal
        self.calls = 0

    def available(self) -> bool:
        return True

    def chat_json(self, system, user, max_tokens=1200):
        self.calls += 1
        if self.gagal:
            raise LLMError("HTTP 500 (uji)")
        return dict(PLAN_JSON)

    def chat(self, system, user, json_mode=False, max_tokens=1200):
        self.calls += 1
        if self.gagal:
            raise LLMError("HTTP 500 (uji)")
        return DRAF_LLM


# --------------------------------------------------------------------------- 1. planner
fake = FakeLLM()
planner = PlannerAgent(llm=fake)
plan = planner(BRIEF, "AY-SR-101", "tiktok")
cek("W-01", "Planner memakai JSON dari model (mode=llm)", plan.mode == "llm", f"mode={plan.mode}")
cek("W-02", "Identitas rencana tidak dipercaya dari model",
    plan.sku == "AY-SR-101" and plan.platform == "tiktok", f"{plan.sku}/{plan.platform}")
cek("W-03", "Fakta dari model masuk ke rencana",
    any("niacinamide" in f for f in plan.fakta_boleh), f"{len(plan.fakta_boleh)} fakta")

# --------------------------------------------------------------------------- 2. writer
writer = WriterAgent(llm=fake)
draf = writer(plan, None, 1)
cek("W-04", "Writer memakai teks dari model",
    "Merawat kulit nggak perlu janji berlebihan" in draf, f"{len(draf)} karakter")

# --------------------------------------------------------------------------- 3. gagal -> fallback
p2 = PlannerAgent(llm=FakeLLM(gagal=True))(BRIEF, "AY-SR-101", "tiktok")
cek("W-05", "Planner gagal -> turun ke deterministik, tidak crash",
    p2.mode == "fallback" and bool(p2.fakta_boleh), f"mode={p2.mode}")
cek("W-06", "Alasan kegagalan tercatat di rencana",
    "LLM gagal" in p2.catatan, p2.catatan[-40:])

d2 = WriterAgent(llm=FakeLLM(gagal=True))(p2, None, 1)
cek("W-07", "Writer gagal -> tetap menghasilkan draf yang bisa dinilai",
    len(d2) > 100, f"{len(d2)} karakter")

# --------------------------------------------------------------------------- 4. pipeline penuh
log = AuditLog()
pipe = ContentPipeline(reviewer=Reviewer(audit=log), log=log, gate=ApprovalGate(log))
hasil = pipe.run(BRIEF, "AY-SR-101", "tiktok",
                 planner=PlannerAgent(llm=FakeLLM()), writer=WriterAgent(llm=FakeLLM()))
cek("W-08", "Pipeline dengan LLM tetap lewat Reviewer dan approval",
    hasil.status == "TERBIT" and bool(hasil.plan_id), f"{hasil.status}, plan {hasil.plan_id}")
cek("W-09", "Mode planner tercatat di hasil",
    hasil.mode_planner == "llm", f"mode={hasil.mode_planner}")

# --------------------------------------------------------------------------- 5. budget
cfg = LLMConfig(base_url="https://contoh.invalid/v1", api_key="sk-uji", model="uji", max_calls=2)
klien = LLMClient(cfg)
klien.calls = cfg.max_calls          # pura-pura budget sudah habis, tanpa jaringan
pesan = ""
try:
    klien.chat("s", "u")
except LLMBudgetError as e:
    pesan = str(e)
except LLMError as e:
    pesan = f"error lain: {e}"
cek("W-10", "Budget panggilan menghentikan pemakaian berlebih",
    "budget panggilan habis" in pesan, pesan[:60])

# --------------------------------------------------------------------------- 6. tanpa key
cfg2 = LLMConfig(base_url="", api_key="", model="")
cek("W-12", "URL chat digabung benar (tanpa garis miring ganda/hilang)",
    LLMClient(cfg)._url() == "https://contoh.invalid/v1/chat/completions",
    LLMClient(cfg)._url())
cek("W-11", "Tanpa konfigurasi, klien menyatakan belum siap (bukan error)",
    not LLMClient(cfg2).available(), LLMConfig().alasan_tidak_siap() or "kosong")

# --------------------------------------------------------------------------- cetak
print(f"{'kode':6s} {'uji':58s} hasil")
print("-" * 92)
for kode, nama, ok, detail in baris:
    print(f"{kode:6s} {nama:58s} {'PASS' if ok else 'FAIL':4s}  {detail}")
lulus = sum(1 for b in baris if b[2])
print("-" * 92)
print(f"{lulus}/{len(baris)} lulus")
print("\nCatatan: ini menguji JALUR, bukan kualitas model. Kualitas hanya bisa dinilai")
print("setelah API key terpasang dan 5 draf nyata dijalankan.")
raise SystemExit(0 if lulus == len(baris) else 1)
