"""
agents — Planner & Writer untuk Challenge C, dipisah dari `engine/`.

Kenapa dipisah:
  engine/  = Reviewer + governance + orkestrator. Bagian yang TIDAK boleh berubah
             seenaknya karena ia yang menegakkan aturan.
  agents/  = dua peran yang boleh diganti. Timmu bisa memakai agent di sini,
             atau agent buatan rekan tim, tanpa menyentuh Reviewer.

Kontrak yang mengikat keduanya (lihat contract.py):
    planner(brief: str, sku: str, platform: str) -> Plan
    writer(plan: Plan, feedback: list[dict] | None, iterasi: int) -> str

Pemakaian:
    from agents import load_agents
    planner, writer = load_agents("mine")     # agent di folder ini
    planner, writer = load_agents("team")     # agent rekan tim (lewat env)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
DATA = ROOT / "dataset_c"

# Reviewer & governance tinggal di engine/. Tambahkan ke path supaya agent bisa
# mengimpornya tanpa memaksa pemanggil mengatur sys.path sendiri.
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from .contract import ContractError, Plan, validate_draft, validate_plan  # noqa: E402

# registry & agent diimpor malas: supaya `python -m agents.planner` tidak
# memuat modul yang sama dua kali (memicu RuntimeWarning).
_LAZY = {"load_agents": "registry", "describe": "registry"}


def __getattr__(nama):
    if nama in _LAZY:
        import importlib
        mod = importlib.import_module(f".{_LAZY[nama]}", __name__)
        return getattr(mod, nama)
    raise AttributeError(nama)


__all__ = ["ContractError", "Plan", "validate_draft", "validate_plan",
           "load_agents", "describe", "ENGINE", "DATA", "ROOT"]
