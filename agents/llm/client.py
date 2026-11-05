"""
client.py — pemanggil model untuk Planner & Writer.

Prinsip yang dipegang:

  1. TIDAK ADA API KEY = TETAP JALAN. Agent jatuh ke mode deterministik, bukan crash.
     Kamu bisa menguji seluruh loop hari ini tanpa membayar apa pun.
  2. Provider tidak dikunci. Semua yang bicara format OpenAI-compatible
     (/chat/completions) bisa dipakai: DeepSeek, OpenAI, Gemini-compat, Ollama,
     maupun Tencent TokenHub.
  3. Budget dibatasi. Satu konten maksimal 9 panggilan (3 agent x 3 iterasi).
     Lewat dari itu = bug, bukan kebutuhan.
  4. Kegagalan tidak pernah diam. Setiap error punya tipe, dan pemanggil wajib
     memutuskannya — bukan menganggap "kosong berarti aman".

Konfigurasi lewat environment (jangan pernah menaruh key di kode):

    LLM_BASE_URL   https://api.deepseek.com/v1
    LLM_API_KEY    sk-...
    LLM_MODEL      deepseek-chat
    LLM_CHAT_PATH  /chat/completions        (opsional; override bila provider beda)
    LLM_TIMEOUT    30                       (detik)
    LLM_MAX_CALLS  9
    LLM_TEMPERATURE 0.4

Contoh .env untuk beberapa provider ada di agents/.env.example
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ..contract import parse_json_loose

# Preset yang sudah diketahui bentuknya. Bukan daftar tertutup — provider lain
# tetap bisa dipakai selama formatnya OpenAI-compatible.
PRESET = {
    "openai":   {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "tokenhub": {"base_url": "https://tokenhub.tencentmaas.com/plan/v3",
                 "model": "deepseek-v4-flash-202605"},
    "ollama":   {"base_url": "http://localhost:11434/v1", "model": "llama3.1"},
}


class LLMError(RuntimeError):
    """Kegagalan yang bisa dijelaskan: jaringan, status HTTP, atau keluaran tak terbaca."""

    def __init__(self, pesan: str, *, status: int | None = None, body: str = ""):
        self.status = status
        self.body = (body or "")[:400]
        super().__init__(pesan)


class LLMBudgetError(LLMError):
    """Terlalu banyak panggilan untuk satu konten — indikasi loop tak terkendali."""


@dataclass
class LLMConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    chat_path: str = "/chat/completions"
    timeout: int = 30
    max_calls: int = 9
    temperature: float = 0.4
    provider: str = "custom"

    # ---------------------------------------------------------------- pabrik
    @classmethod
    def from_env(cls) -> "LLMConfig":
        prov = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
        preset = PRESET.get(prov, {})
        return cls(
            base_url=(os.environ.get("LLM_BASE_URL") or preset.get("base_url", "")).rstrip("/"),
            api_key=os.environ.get("LLM_API_KEY", "").strip(),
            model=(os.environ.get("LLM_MODEL") or preset.get("model", "")).strip(),
            chat_path=os.environ.get("LLM_CHAT_PATH", "/chat/completions"),
            timeout=int(os.environ.get("LLM_TIMEOUT", "30")),
            max_calls=int(os.environ.get("LLM_MAX_CALLS", "9")),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.4")),
            provider=prov or "custom",
        )

    def alasan_tidak_siap(self) -> str:
        """Kosong berarti siap dipakai. Selain itu, jelaskan apa yang kurang."""
        if not self.base_url:
            return "LLM_BASE_URL belum diisi"
        if not self.model:
            return "LLM_MODEL belum diisi"
        if "localhost" not in self.base_url and "127.0.0.1" not in self.base_url \
                and not self.api_key:
            return "LLM_API_KEY belum diisi"
        return ""

    def ringkas(self) -> str:
        """Ringkasan aman untuk dicetak — API key tidak pernah ditampilkan."""
        k = "—" if not self.api_key else f"{self.api_key[:4]}…{self.api_key[-4:]}"
        return (f"provider={self.provider} model={self.model or '—'} "
                f"base={self.base_url or '—'} key={k}")


class LLMClient:
    def __init__(self, config: LLMConfig | None = None):
        self.cfg = config or LLMConfig.from_env()
        self.calls = 0
        self.last_error: str = ""

    # ---------------------------------------------------------------- status
    def available(self) -> bool:
        return not self.cfg.alasan_tidak_siap()

    def sisa_budget(self) -> int:
        return max(0, self.cfg.max_calls - self.calls)

    def _url(self) -> str:
        return f"{self.cfg.base_url.rstrip('/')}/{self.cfg.chat_path.lstrip('/')}"

    # ---------------------------------------------------------------- panggil
    def chat(self, system: str, user: str, *, json_mode: bool = False,
             max_tokens: int = 1200) -> str:
        if not self.available():
            raise LLMError(f"LLM tidak siap: {self.cfg.alasan_tidak_siap()}")
        if self.calls >= self.cfg.max_calls:
            raise LLMBudgetError(
                f"budget panggilan habis ({self.calls}/{self.cfg.max_calls}). "
                "Satu konten seharusnya cukup <= 9 panggilan; lebih dari itu "
                "menandakan loop atau retry yang tidak terkendali.")

        payload = {
            "model": self.cfg.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": self.cfg.temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            self._url(),
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.cfg.api_key}"},
            method="POST",
        )
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout) as r:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")[:400]
            hint = ""
            if e.code == 404:
                hint = (" (404: kemungkinan LLM_CHAT_PATH salah untuk provider ini — "
                        "coba /chat/completions atau /v1/chat/completions)")
            elif e.code in (401, 403):
                hint = " (401/403: API key salah atau tidak berhak untuk model ini)"
            elif e.code == 429:
                hint = " (429: kena rate limit / kuota)"
            self.last_error = f"HTTP {e.code}{hint}"
            raise LLMError(f"HTTP {e.code}{hint}", status=e.code, body=body) from e
        except urllib.error.URLError as e:
            self.last_error = f"jaringan: {e.reason}"
            raise LLMError(f"gagal menghubungi {self._url()}: {e.reason}") from e
        except json.JSONDecodeError as e:
            self.last_error = "respons bukan JSON"
            raise LLMError("respons provider bukan JSON") from e

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            self.last_error = "bentuk respons tidak dikenal"
            raise LLMError(f"bentuk respons provider tidak dikenal: {str(data)[:200]}") from e

    def chat_json(self, system: str, user: str, *, max_tokens: int = 1200) -> dict:
        """Panggil model dan paksa hasilnya bisa dibaca sebagai objek JSON."""
        teks = self.chat(system, user, json_mode=True, max_tokens=max_tokens)
        try:
            return parse_json_loose(teks)
        except (ValueError, json.JSONDecodeError) as e:
            raise LLMError(f"keluaran model bukan JSON yang sah: {e}") from e


# --------------------------------------------------------------------------- CLI
def _main() -> int:
    import sys

    cfg = LLMConfig.from_env()
    c = LLMClient(cfg)
    print("konfigurasi :", cfg.ringkas())
    kurang = cfg.alasan_tidak_siap()
    if kurang:
        print("status      : BELUM SIAP —", kurang)
        print("\nAgent tetap bisa dipakai dalam mode deterministik.")
        print("Isi variabel berikut untuk mengaktifkan LLM (lihat agents/.env.example):")
        for k in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
            print(f"  {k}")
        return 0

    print("status      : siap")
    if "--ping" not in sys.argv:
        print("\nJalankan dengan --ping untuk menguji satu panggilan sungguhan.")
        return 0

    print("\nmengirim satu panggilan uji…")
    try:
        out = c.chat("Jawab sangat singkat.", "Balas dengan satu kata: siap")
        print(f"OK · {c.calls} panggilan · jawaban: {out.strip()[:80]!r}")
        return 0
    except LLMError as e:
        print(f"GAGAL · {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
