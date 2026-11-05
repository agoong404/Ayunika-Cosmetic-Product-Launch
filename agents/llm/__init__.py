"""Lapisan LLM untuk agents/. Satu antarmuka, provider bisa diganti."""

__all__ = ["LLMClient", "LLMConfig", "LLMError", "LLMBudgetError"]


def __getattr__(nama):
    # Impor malas: supaya `python -m agents.llm.client` tidak memuat modul yang
    # sama dua kali (memicu RuntimeWarning).
    if nama in __all__:
        from . import client
        return getattr(client, nama)
    raise AttributeError(nama)
