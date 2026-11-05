"""
layer2.py — Reviewer lapis-2: penilaian model, dengan penjaga kutipan.

Kenapa lapis ini ada:
  Lapis-1 (kode) hanya bisa memeriksa yang berbentuk pola: angka, frasa terlarang,
  nomor sertifikat, jumlah emoji. Ia tidak bisa menilai apakah sebuah kalimat
  *terdengar* seperti janji, atau apakah klaimnya bisa diverifikasi.

  Contoh nyata yang lolos lapis-1: "dua bahan yang paling banyak diteliti".
  Tidak ada kata di daftar terlarang, tapi klaimnya tidak bisa dibuktikan dari
  lembar produk.

Kenapa penjaganya ketat:
  Model bisa mengarang pelanggaran. Karena itu SETIAP temuan wajib membawa kutipan
  yang benar-benar ada di draf. Yang tidak ada, dibuang — dan pembuangannya dicatat,
  bukan disembunyikan.

Wewenang lapis-2 dibatasi 6 aturan: R-04, R-05, R-07, R-08, R-10, R-12.
Aturan lain tetap milik kode. Model yang melaporkan aturan di luar itu ditolak,
supaya ia tidak mengulang (dan mengacaukan) pekerjaan lapis-1.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "dataset_c"
PROMPT = Path(__file__).resolve().parent / "prompts" / "reviewer_lapis2_v1.md"


class Layer2:
    # Aturan yang boleh dinilai model. Di luar ini ditolak.
    KODE = ("R-04", "R-05", "R-07", "R-08", "R-10", "R-12")

    def __init__(self, llm=None, reviewer=None, data_dir: Path = DATA):
        self.llm = llm
        self.reviewer = reviewer              # dipakai untuk apply_llm_findings()
        self.data = data_dir
        self.products = {r["sku"]: r for r in self._rows("products.csv")}
        self.sheets = {p.name: p.read_text(encoding="utf-8")
                       for p in (data_dir / "product_sheets").glob("PS-*.md")}
        tone = data_dir / "brand_tone_guide.md"
        self.tone = tone.read_text(encoding="utf-8") if tone.exists() else ""

    def _rows(self, nama: str) -> list[dict]:
        with open(self.data / nama, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _sheet(self, sku: str) -> str:
        for teks in self.sheets.values():
            if f"sku: {sku}" in teks:
                return teks
        return ""

    def available(self) -> bool:
        return bool(self.llm) and self.llm.available()

    # ------------------------------------------------------------------ prompt
    def build_prompt(self, draft: str, sku: str, platform: str) -> tuple[str, str]:
        system = PROMPT.read_text(encoding="utf-8")
        sheet = self._sheet(sku)
        p = self.products.get(sku, {})
        user = (
            f"## Produk\n{p.get('nama_produk', sku)} · {p.get('kategori', '')}\n\n"
            f"## Lembar produk (satu-satunya sumber fakta)\n{sheet}\n\n"
            f"## Nada merek\n{self.tone}\n\n"
            f"## Platform\n{platform}\n\n"
            f"## Draf yang dinilai\n<<<DRAF\n{draft}\nDRAF>>>\n\n"
            "Nilai draf di atas. Balas hanya JSON."
        )
        return system, user

    # ------------------------------------------------------------------ penjaga
    def guard(self, draft: str, findings: list[dict]) -> tuple[list, list[dict]]:
        """
        Saring temuan model sebelum masuk verdict.

        Dua saringan:
          1. wewenang — hanya 6 aturan lapis-2
          2. kutipan — span harus ada persis di draf (via Reviewer.apply_llm_findings)

        Keduanya mencatat apa yang dibuang, supaya bisa diaudit.
        """
        if not isinstance(findings, list):
            return [], [{"alasan_tolak": "findings bukan daftar", "mentah": str(findings)[:200]}]

        wewenang, luar = [], []
        for f in findings:
            if not isinstance(f, dict):
                luar.append({"alasan_tolak": "bukan objek", "mentah": str(f)[:120]})
                continue
            if f.get("rule_id") not in self.KODE:
                luar.append({**f, "alasan_tolak": "di luar wewenang lapis-2"})
                continue
            wewenang.append(f)

        if self.reviewer is None:
            return [], luar + [{**f, "alasan_tolak": "tidak ada Reviewer untuk verifikasi"}
                               for f in wewenang]

        diterima, dibuang = self.reviewer.apply_llm_findings(draft, wewenang)
        return diterima, luar + dibuang

    # ------------------------------------------------------------------ jalankan
    def run(self, draft: str, sku: str, platform: str) -> dict:
        """Panggil model lalu saring hasilnya. Tidak pernah melempar ke pemanggil."""
        if not self.available():
            return {"diterima": [], "dibuang": [], "mentah": 0, "aktif": False, "error": ""}
        system, user = self.build_prompt(draft, sku, platform)
        try:
            data = self.llm.chat_json(system, user, max_tokens=900)
        except Exception as e:                    # noqa: BLE001 — lapis-2 tidak boleh menjatuhkan review
            return {"diterima": [], "dibuang": [], "mentah": 0, "aktif": True,
                    "error": f"{type(e).__name__}: {e}"}

        findings = data.get("findings", []) if isinstance(data, dict) else []
        diterima, dibuang = self.guard(draft, findings)
        return {"diterima": [v.as_dict() for v in diterima], "dibuang": dibuang,
                "mentah": len(findings), "aktif": True, "error": ""}

    # ------------------------------------------------------------------ dari berkas
    def from_text(self, draft: str, teks: str) -> dict:
        """Untuk jalur WorkBuddy: JSON yang ditempel manual, disaring dengan penjaga sama."""
        try:
            t = teks.strip()
            if t.startswith("```"):
                t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t)
            data = json.loads(t)
        except json.JSONDecodeError as e:
            return {"diterima": [], "dibuang": [{"alasan_tolak": f"JSON tidak sah: {e}"}],
                    "mentah": 0, "aktif": True, "error": f"JSON tidak sah: {e}"}
        findings = data.get("findings", []) if isinstance(data, dict) else []
        diterima, dibuang = self.guard(draft, findings)
        return {"diterima": [v.as_dict() for v in diterima], "dibuang": dibuang,
                "mentah": len(findings), "aktif": True, "error": ""}


# --------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from reviewer import Reviewer

    sku = sys.argv[2] if len(sys.argv) > 2 else "AY-SR-101"
    plat = sys.argv[3] if len(sys.argv) > 3 else "tiktok"
    berkas = sys.argv[1] if len(sys.argv) > 1 else None
    if not berkas:
        print("pakai: python layer2.py <draf.md> [SKU] [platform]")
        raise SystemExit(1)

    teks = Path(berkas).read_text(encoding="utf-8")
    L = Layer2(reviewer=Reviewer())
    system, user = L.build_prompt(teks, sku, plat)
    print("=" * 78)
    print("PROMPT SISTEM")
    print("=" * 78)
    print(system)
    print("=" * 78)
    print("PROMPT PENGGUNA")
    print("=" * 78)
    print(user)
