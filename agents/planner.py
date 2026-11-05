"""
planner.py — Planner Agent (Challenge C).

Tugasnya sempit dan sengaja dibuat sempit: mengubah brief + lembar produk menjadi
rencana terstruktur. Ia TIDAK menulis konten, dan TIDAK memutuskan boleh/tidak —
itu tugas Reviewer.

Dua mode:
  llm           — memakai model, prompt di llm/prompts/planner_v1.md
  deterministik — mem-parse lembar produk dan brief dengan aturan tetap

Mode deterministik bukan sekadar cadangan: ia membuat seluruh pipeline bisa diuji
tanpa API key, dan menjadi pembanding saat menilai keluaran model.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from .contract import Plan, validate_plan, BATAS
from .llm.client import LLMClient, LLMError

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dataset_c"
PROMPTS = Path(__file__).resolve().parent / "llm" / "prompts"

STRUKTUR = {
    "tiktok": ["HOOK", "ISI", "CTA"],
    "instagram": ["baris pembuka", "isi", "ajakan"],
    "marketplace": ["judul", "poin deskripsi"],
}


def rupiah(nilai: str) -> str:
    """'149000' -> 'Rp149.000'. String kosong tetap kosong."""
    angka = re.sub(r"\D", "", str(nilai or ""))
    if not angka:
        return ""
    return "Rp" + f"{int(angka):,}".replace(",", ".")


class PlannerAgent:
    def __init__(self, llm: LLMClient | None = None, data_dir: Path = DATA):
        self.data = data_dir
        self.llm = llm
        self.products = {r["sku"]: r for r in self._rows("products.csv")}
        self.sheets = {p.name: p.read_text(encoding="utf-8")
                       for p in (self.data / "product_sheets").glob("PS-*.md")}
        self.brief = (self.data / "briefs" / "BRF-101_launch_bright_serum.md").read_text(encoding="utf-8")
        self.specs = (self.data / "platform_specs.md").read_text(encoding="utf-8")

    def _rows(self, nama: str) -> list[dict]:
        with open(self.data / nama, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    # ------------------------------------------------------------------ bahan
    def _sheet(self, sku: str) -> str:
        for teks in self.sheets.values():
            if f"sku: {sku}" in teks:
                return teks
        return ""

    @staticmethod
    def _klaim_boleh(sheet: str) -> list[str]:
        """Ambil butir bernomor di bawah '## Klaim yang BOLEH'.

        Hanya teks di dalam tanda kutip yang diambil — lembar produk kadang
        menambahkan anotasi setelah kutipan (mis. '← satu-satunya SKU yang boleh')
        dan anotasi itu bukan bagian dari klaim.
        """
        m = re.search(r"##\s*Klaim yang BOLEH(.*?)(?:\n##|\Z)", sheet, re.S)
        if not m:
            return []
        out = []
        for baris in m.group(1).splitlines():
            k = re.match(r'\s*\d+\.\s*"([^"]+)"', baris)
            if k:
                out.append(re.sub(r"\s+", " ", k.group(1)).strip())
                continue
            k = re.match(r"\s*\d+\.\s*(.+)$", baris)
            if k:
                teks = re.sub(r"\s+", " ", k.group(1)).strip()
                teks = teks.split("←")[0].strip().strip('"').strip()
                if teks:
                    out.append(teks)
        return out

    @staticmethod
    def _klaim_dilarang(sheet: str) -> list[str]:
        m = re.search(r"##\s*Klaim yang DILARANG(.*?)(?:\n##|\Z)", sheet, re.S)
        if not m:
            return []
        out = []
        for baris in m.group(1).splitlines():
            if baris.strip().startswith("|") and "---" not in baris:
                sel = [c.strip() for c in baris.strip().strip("|").split("|")]
                if sel and sel[0] and sel[0].lower() not in ("klaim",):
                    out.append(sel[0].replace("**", ""))
        return out

    def _pesan_brief(self) -> tuple[list[str], list[str]]:
        """Pisahkan pesan kunci brief menjadi yang boleh dan yang tidak."""
        boleh, dilarang = [], []
        for teks, tanda in re.findall(r'^\d+\.\s+"(.+?)"\s*(✅|❌)', self.brief, re.M):
            (boleh if tanda == "✅" else dilarang).append(teks.strip())
        return boleh, dilarang

    # ------------------------------------------------------------------ rencana
    def _rencana_deterministik(self, sku: str, platform: str) -> Plan:
        p = self.products[sku]
        sheet = self._sheet(sku)
        boleh_sheet = self._klaim_boleh(sheet)
        boleh_brief, dilarang_brief = self._pesan_brief()

        # Fakta boleh = klaim dari lembar produk (sumber otoritatif) + pesan brief
        # yang ditandai boleh. Brief tidak boleh menambah fakta baru di luar sheet,
        # jadi pesan brief hanya dipakai bila benar-benar berasal dari sheet.
        gabung = list(boleh_sheet)
        for b in boleh_brief:
            if b not in gabung:
                gabung.append(b)

        promo = p.get("harga_promo", "").strip()
        return Plan(
            sku=sku,
            nama=p["nama_produk"],
            kategori=p.get("kategori", ""),
            platform=platform,
            angle=("Jelaskan bahan aktif dan tekstur apa adanya, tanpa janji hasil. "
                   "Fokus pada satu alasan masuk akal untuk mencoba."),
            struktur=STRUKTUR[platform],
            fakta_boleh=gabung,
            fakta_dilarang=self._klaim_dilarang(sheet) + dilarang_brief,
            harga=rupiah(p.get("harga", "")),
            harga_promo=rupiah(promo) if promo else "",
            bpom=p.get("notifikasi_bpom", ""),
            isi=p.get("isi", ""),
            disclaimer="Hasil dapat berbeda pada setiap orang.",
            emoji_maks=BATAS[platform]["emoji_maks"],
            catatan=("Sebutkan angka hanya bila tercantum di fakta_boleh. "
                     "Jangan menyinggung halal kecuali ada di fakta_boleh beserta nomornya."),
            sumber=[f"PS-{sku}", "BRF-101", "platform_specs.md"],
            mode="deterministik",
        )

    # ------------------------------------------------------------------ prompt
    def build_prompt(self, sku: str, platform: str) -> tuple[str, str]:
        """
        Susun (system, user) untuk Planner. Dipakai jalur LLM maupun jembatan
        WorkBuddy — supaya prompt yang dilihat model selalu sama persis.
        """
        system = (PROMPTS / "planner_v1.md").read_text(encoding="utf-8")
        p = self.products[sku]
        user = (
            f"## SKU\n{sku} — {p['nama_produk']}\n\n"
            f"## Platform\n{platform}\n\n"
            f"## Brief\n{self.brief}\n\n"
            f"## Lembar produk\n{self._sheet(sku)}\n\n"
            f"## Spesifikasi platform\n{self.specs}\n\n"
            "Susun rencana untuk SKU dan platform di atas. Balas hanya JSON."
        )
        return system, user

    def plan_from_model(self, data: dict, sku: str, platform: str,
                        mode: str = "llm") -> Plan:
        """Terapkan aturan yang tidak boleh diserahkan ke model, lalu validasi."""
        plan = Plan.from_dict(data, pembuat="planner-agent")
        # Identitas dan batas platform TIDAK dipercaya dari keluaran model.
        plan.sku, plan.platform = sku, platform
        plan.nama = plan.nama or self.products[sku]["nama_produk"]
        plan.kategori = plan.kategori or self.products[sku].get("kategori", "")
        plan.emoji_maks = min(plan.emoji_maks, BATAS[platform]["emoji_maks"])
        plan.mode = mode
        return validate_plan(plan, "planner-agent")

    def _rencana_llm(self, sku: str, platform: str) -> Plan:
        system, user = self.build_prompt(sku, platform)
        return self.plan_from_model(self.llm.chat_json(system, user), sku, platform)

    # ------------------------------------------------------------------ panggil
    def __call__(self, brief: str, sku: str, platform: str) -> Plan:
        if sku not in self.products:
            raise KeyError(f"SKU {sku} tidak ada di registri produk")
        if self.llm and self.llm.available():
            try:
                return validate_plan(self._rencana_llm(sku, platform), "planner-agent")
            except (LLMError, ValueError) as e:
                # Gagal LLM tidak boleh menghentikan kampanye: turun ke deterministik,
                # tapi jejaknya harus terlihat (mode=fallback + alasan).
                plan = self._rencana_deterministik(sku, platform)
                plan.mode = "fallback"
                plan.catatan = f"{plan.catatan} [LLM gagal: {e}]"
                return validate_plan(plan, "planner-agent")
        return validate_plan(self._rencana_deterministik(sku, platform), "planner-agent")


# --------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    import json
    import sys

    sku = sys.argv[1] if len(sys.argv) > 1 else "AY-SR-101"
    plat = sys.argv[2] if len(sys.argv) > 2 else "tiktok"
    llm = LLMClient()
    ag = PlannerAgent(llm=llm)
    plan = ag(ag.brief, sku, plat)
    print(f"mode: {plan.mode}")
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
