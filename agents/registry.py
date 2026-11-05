"""
registry.py — memilih Planner & Writer yang dipakai, tanpa mengubah orkestrator.

Empat sumber agent:

  mine      agent di folder ini (PlannerAgent + WriterAgent)
  team      agent buatan rekan tim, dimuat lewat env TEAM_AGENTS_MODULE
  stub      TemplatePlanner + ScriptedWriter dari engine/ (pengganti lama)
  <skenario> writer yang sengaja dirusak untuk menguji loop (lihat FAULT di bawah)

Semua jalur melewati adaptor yang sama, jadi bentuk keluaran apa pun divalidasi
sebelum masuk pipeline. Agent tim yang mengembalikan bentuk salah akan gagal dengan
pesan jelas, bukan KeyError di tengah loop.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from .contract import ContractError, validate_draft, validate_plan
from .planner import PlannerAgent
from .writer import WriterAgent

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))


# --------------------------------------------------------------------------- adaptor
def _adapt_planner(fn, nama: str):
    def panggil(brief, sku, platform):
        try:
            keluaran = fn(brief, sku, platform)
        except ContractError:
            raise
        except Exception as e:                       # noqa: BLE001 — ingin dilaporkan, bukan disembunyikan
            raise ContractError(nama, [f"melempar {type(e).__name__}: {e}"]) from e
        return validate_plan(keluaran, nama)
    return panggil


def _adapt_writer(fn, nama: str):
    def panggil(plan, feedback, iterasi):
        try:
            keluaran = fn(plan, feedback, iterasi)
        except ContractError:
            raise
        except Exception as e:                       # noqa: BLE001
            raise ContractError(nama, [f"melempar {type(e).__name__}: {e}"]) from e
        return validate_draft(keluaran, plan, nama)
    return panggil


# --------------------------------------------------------------------------- skenario rusak
def _stubborn(base):
    """Selalu mengembalikan draf pertama — Writer yang tidak belajar dari catatan."""
    cache: dict[int, str] = {}

    def panggil(plan, feedback, iterasi):
        if 1 not in cache:
            cache[1] = base(plan, feedback, 1)
        return cache[1]
    return panggil


def _crash(base, pada_iterasi: int = 2):
    """Melempar exception di tengah loop — menguji penanganan error orkestrator."""
    def panggil(plan, feedback, iterasi):
        if iterasi >= pada_iterasi:
            raise RuntimeError(f"writer-agent gagal pada iterasi {iterasi} (skenario uji)")
        return base(plan, feedback, iterasi)
    return panggil


# Draf manusia per platform. TikTok punya v1/v2/v3 (14 -> 4 -> 0 temuan);
# Instagram & marketplace punya v1/v2 (9 -> 0 dan 8 -> 0).
DRAF_PLATFORM = {
    "tiktok": ["DRAFT-101_v1.md", "DRAFT-101_v2.md", "DRAFT-101_v3.md"],
    "instagram": ["DRAFT-101-ig_v1.md", "DRAFT-101-ig_v2.md"],
    "marketplace": ["DRAFT-101-mkt_v1.md", "DRAFT-101-mkt_v2.md"],
}


def _scripted(platform: str | None = None):
    """Draf manusia v1 → v2 → v3: siklus tolak → perbaiki → setuju yang sungguhan."""
    from reviewer import strip_markdown
    import re as _re

    folder = ROOT / "dataset_c" / "sample_drafts"
    nama = DRAF_PLATFORM.get(platform or "tiktok", DRAF_PLATFORM["tiktok"])
    drafts = []
    for n in nama:
        t = (folder / n).read_text(encoding="utf-8")
        drafts.append(strip_markdown(_re.sub(r"^---.*?---", "", t, flags=_re.S)))

    def panggil(plan, feedback, iterasi):
        return drafts[min(iterasi - 1, len(drafts) - 1)]
    return panggil


# --------------------------------------------------------------------------- tim
def _dari_tim(modul: str):
    """
    Muat agent rekan tim. Modul harus menyediakan `planner` dan `writer`,
    atau kelas `PlannerAgent` / `WriterAgent`.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        m = importlib.import_module(modul)
    except ImportError as e:
        raise SystemExit(
            f"Tidak bisa memuat modul agent tim '{modul}': {e}\n"
            f"Set TEAM_AGENTS_MODULE ke nama modul Python, mis. TEAM_AGENTS_MODULE=tim.agents"
        ) from e

    planner = getattr(m, "planner", None)
    writer = getattr(m, "writer", None)
    if planner is None and hasattr(m, "PlannerAgent"):
        planner = m.PlannerAgent()
    if writer is None and hasattr(m, "WriterAgent"):
        writer = m.WriterAgent()
    if planner is None or writer is None:
        raise SystemExit(
            f"Modul '{modul}' tidak menyediakan planner/writer.\n"
            "Kontrak: planner(brief, sku, platform) -> Plan | dict\n"
            "         writer(plan, feedback, iterasi) -> str"
        )
    return planner, writer


# --------------------------------------------------------------------------- publik
FAULT = ("stubborn", "scripted", "crash")


def load_agents(kind: str = "mine", llm=None, kind_platform: str | None = None):
    """
    Kembalikan (planner, writer) siap dipakai ContentPipeline.

    kind:
      mine | team | stub | stubborn | scripted | crash
    """
    kind = (kind or "mine").lower()

    if kind == "team":
        modul = os.environ.get("TEAM_AGENTS_MODULE", "")
        if not modul:
            raise SystemExit(
                "TEAM_AGENTS_MODULE belum diisi. Contoh:\n"
                '  TEAM_AGENTS_MODULE=tim.agents python -m agents.harness --agents team'
            )
        p, w = _dari_tim(modul)
        return (_adapt_planner(p, f"planner-tim({modul})"),
                _adapt_writer(w, f"writer-tim({modul})"))

    if kind == "stub":
        from pipeline import ScriptedWriter, TemplatePlanner
        drafts = sorted((ROOT / "dataset_c" / "sample_drafts").glob("DRAFT-101_v*.md"))
        return (_adapt_planner(TemplatePlanner(), "planner-stub"),
                _adapt_writer(ScriptedWriter(drafts), "writer-stub"))

    planner = PlannerAgent(llm=llm)
    writer = WriterAgent(llm=llm)
    p_ok = _adapt_planner(planner, "planner-agent")
    w_ok = _adapt_writer(writer, "writer-agent")

    if kind == "stubborn":
        # Ditumpuk pada draf v1 yang memang melanggar — kalau ditumpuk pada writer
        # yang sudah patuh, "tidak belajar" tidak akan pernah terlihat.
        return p_ok, _adapt_writer(_stubborn(_scripted("tiktok")), "writer-stubborn")
    if kind == "crash":
        return p_ok, _adapt_writer(_crash(_scripted("tiktok")), "writer-crash")
    if kind == "scripted":
        return p_ok, _adapt_writer(_scripted(kind_platform), "writer-scripted")
    return p_ok, w_ok


def describe() -> str:
    baris = [
        "Kontrak agent:",
        "  planner(brief: str, sku: str, platform: str) -> Plan | dict",
        "  writer(plan: Plan, feedback: list[dict] | None, iterasi: int) -> str",
        "",
        "Pilihan --agents:",
        "  mine      agent di folder ini (default)",
        "  team      agent rekan tim (butuh TEAM_AGENTS_MODULE)",
        "  stub      pengganti lama di engine/pipeline.py",
        "  stubborn  writer yang tidak belajar dari catatan (uji eskalasi)",
        "  scripted  draf manusia v1→v2→v3 (uji siklus penuh)",
        "  crash     writer gagal di iterasi 2 (uji penanganan error)",
    ]
    return "\n".join(baris)


if __name__ == "__main__":
    print(describe())
