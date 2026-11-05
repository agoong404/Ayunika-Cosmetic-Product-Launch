"""
writer.py — Writer Agent (Challenge C).

Menulis konten dari rencana Planner. Yang sengaja TIDAK ia terima:

  · rulebook lengkap (R-01..R-21)
  · daftar frasa terlarang

Alasannya bukan teknis. Penulis konten bukan pengawas kepatuhannya sendiri. Kalau
Writer tahu seluruh aturan, ia bisa "menghindari kata" tanpa memahami maksudnya,
dan siklus tolak → perbaiki → setujui tidak akan pernah terjadi. Yang ia terima
hanyalah: fakta yang boleh, fakta yang dilarang, nada merek, dan catatan Reviewer.

Dua mode, sama seperti Planner: llm dan deterministik.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from reviewer import EMOJI_RE

from .contract import BATAS, Plan, validate_draft
from .llm.client import LLMClient, LLMError

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dataset_c"
PROMPTS = Path(__file__).resolve().parent / "llm" / "prompts"

FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def _bersih(teks: str) -> str:
    """Buang pagar kode dan kalimat pembuka yang biasa ditambahkan model."""
    t = teks.strip()
    if t.startswith("```"):
        t = FENCE.sub("", t).strip()
    for awalan in ("berikut", "ini draf", "tentu", "siap", "draft"):
        if t.lower().startswith(awalan) and ":" in t.split("\n")[0]:
            t = t.split("\n", 1)[1].strip() if "\n" in t else t
            break
    return t


class WriterAgent:
    def __init__(self, llm: LLMClient | None = None, data_dir: Path = DATA):
        self.data = data_dir
        self.llm = llm
        self.tone = (self.data / "brand_tone_guide.md").read_text(encoding="utf-8")
        self.specs = (self.data / "platform_specs.md").read_text(encoding="utf-8")
        # Konten yang PERNAH disetujui: sumber nada, bukan sumber fakta.
        arsip = self.data / "approved_content_history" / "approved_posts.json"
        self.approved = json.loads(arsip.read_text(encoding="utf-8")) if arsip.exists() else {}

    # ------------------------------------------------------------------ nada
    def profil_nada(self) -> dict:
        """
        Turunkan pola nada dari konten yang PERNAH disetujui.

        Ini yang membuat "belajar dari riwayat" bisa diperiksa: hasilnya berupa
        nilai konkret, bukan klaim bahwa arsip sudah dibaca.
        """
        posts = self.approved.get("posts", [])
        if not posts:
            return {"sumber": 0, "emoji_maks": 2, "hook_tanya": False,
                    "sebut_sertifikat": False, "contoh": []}
        emoji = max(len(EMOJI_RE.findall(p.get("teks", ""))) for p in posts)
        # pertanyaan pembuka = tanda tanya yang muncul sebelum titik/kutip pertama
        hook_tanya = any(re.match(r"[^.!]*\?", p.get("teks", "")) for p in posts)
        sebut_sertifikat = any("bersertifikat halal" in p.get("teks", "").lower()
                               for p in posts)
        return {"sumber": len(posts), "emoji_maks": min(2, max(1, emoji)),
                "hook_tanya": hook_tanya, "sebut_sertifikat": sebut_sertifikat,
                "contoh": [p.get("id") for p in posts]}

    def _hook(self, plan: Plan) -> str:
        """Hook mengikuti pola arsip: pertanyaan situasi, bukan seruan superlatif."""
        nama = self._nama(plan)
        if self.profil_nada()["hook_tanya"]:
            return f"Kulit butuh perawatan yang tepat? Kenalan sama {nama}."
        return f"Merawat kulit nggak perlu janji berlebihan. Kenalan sama {nama}."

    # ------------------------------------------------------------------ bantu
    @staticmethod
    def _nama(plan: Plan) -> str:
        return plan.nama or "produk Ayunika"

    @staticmethod
    def _klaim(plan: Plan, maks: int = 2) -> list[str]:
        """
        Pilih klaim pendek yang aman dipakai sebagai kalimat isi.

        Klaim halal didahulukan BILA ada di fakta_boleh — artinya produknya memang
        bersertifikat dan nomornya tercantum. Kalau tidak ada, Writer tidak
        menyinggung halal sama sekali.
        """
        bersih = [f.strip().rstrip(".") for f in plan.fakta_boleh if len(f.strip()) <= 95]
        halal = [t for t in bersih if t.lower().startswith("bersertifikat halal")]
        lain = [t for t in bersih if t not in halal]
        return (halal[:1] + lain)[:maks]

    @staticmethod
    def _harga_teks(plan: Plan) -> str:
        if plan.harga_promo:
            return (f"Promo peluncuran {plan.harga_promo} untuk 100 pembeli pertama, "
                    f"dari harga normal {plan.harga}.")
        return f"Harga {plan.harga}."

    # ------------------------------------------------------------------ tiktok
    def _tiktok(self, plan: Plan) -> str:
        nama = self._nama(plan)
        klaim = self._klaim(plan)
        isi = " ".join(k.rstrip(".") + "." for k in klaim) if klaim else "Formula ringan."
        return (
            "HOOK (0–3 dtk)\n"
            f"{self._hook(plan)}\n\n"
            "ISI (3–45 dtk)\n"
            f"{isi} Teksturnya ringan dan cepat meresap, nggak lengket.\n\n"
            "CTA (45–60 dtk)\n"
            f"{self._harga_teks(plan)}\n\n"
            f"{plan.disclaimer}"
        )

    # ------------------------------------------------------------------ instagram
    def _instagram(self, plan: Plan) -> str:
        nama = self._nama(plan)
        klaim = self._klaim(plan, maks=3)
        poin = "\n".join(f"· {k}." for k in klaim) if klaim else ""
        emoji = " 🤍" if self.profil_nada()["emoji_maks"] >= 1 else ""
        return (
            f"{self._hook(plan)}\n\n"
            f"{poin}\n\n"
            f"{self._harga_teks(plan)}\n\n"
            f"{plan.disclaimer}{emoji}\n\n"
            f"{self._tagar(plan)}"
        )

    # ------------------------------------------------------------------ marketplace
    def _marketplace(self, plan: Plan) -> str:
        nama = self._nama(plan)
        judul = f"{nama} {plan.isi}".strip()
        if len(judul) > 70:
            judul = judul[:70].rsplit(" ", 1)[0]
        poin = []
        for k in self._klaim(plan, maks=3):
            poin.append(f"- {k}"[:120])
        poin.append(f"- Isi bersih {plan.isi}"[:120])
        if plan.harga_promo:
            poin.append(f"- Harga promo {plan.harga_promo} (normal {plan.harga})"[:120])
        else:
            poin.append(f"- Harga {plan.harga}"[:120])
        poin.append(f"- Notifikasi BPOM {plan.bpom}"[:120])
        return (f"Judul: {judul}\n\n" + "\n".join(poin) + f"\n\n{plan.disclaimer}")

    @staticmethod
    def _tagar(plan: Plan) -> str:
        """Tagar netral: nama merek + kategori. Tidak boleh memuat klaim."""
        kat = re.sub(r"[^a-z0-9]", "", (plan.kategori or "skincare").lower())
        return f"#ayunika #{kat} #perawatankulit"

    def _deterministik(self, plan: Plan) -> str:
        return {
            "tiktok": self._tiktok,
            "instagram": self._instagram,
            "marketplace": self._marketplace,
        }[plan.platform](plan)

    # ------------------------------------------------------------------ llm
    def build_prompt(self, plan: Plan, feedback: list[dict] | None,
                     iterasi: int) -> tuple[str, str]:
        """Susun (system, user) untuk Writer. Dipakai jalur LLM maupun jembatan WorkBuddy."""
        system = (PROMPTS / "writer_v1.md").read_text(encoding="utf-8")
        bagian = [
            f"## Rencana\n{json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)}",
            f"## Nada merek\n{self.tone}",
            "## Contoh yang PERNAH disetujui (tiru nadanya, jangan salin faktanya)\n"
            + "\n\n".join(f"[{p.get('id')} · {p.get('platform')}] {p.get('teks')}"
                           for p in self.approved.get("posts", [])),
            f"## Spesifikasi platform\n{self.specs}",
            f"## Iterasi\n{iterasi} dari maksimal 3",
        ]
        if feedback:
            bagian.append("## Catatan Reviewer (WAJIB diperbaiki)\n"
                           + json.dumps(feedback, ensure_ascii=False, indent=2))
        else:
            bagian.append("## Catatan Reviewer\n(tidak ada — ini draf pertama)")
        bagian.append(f"Tulis konten untuk platform {plan.platform}. Kirim teksnya saja.")
        return system, "\n\n".join(bagian)

    def _llm(self, plan: Plan, feedback: list[dict] | None, iterasi: int) -> str:
        system, user = self.build_prompt(plan, feedback, iterasi)
        return _bersih(self.llm.chat(system, user, max_tokens=900))

    # ------------------------------------------------------------------ panggil
    def __call__(self, plan: Plan, feedback: list[dict] | None = None,
                 iterasi: int = 1) -> str:
        if self.llm and self.llm.available():
            try:
                return validate_draft(self._llm(plan, feedback, iterasi), plan, "writer-agent")
            except (LLMError, ValueError):
                # Turun ke deterministik; Reviewer tetap menilai hasilnya, jadi
                # tidak ada konten yang lolos tanpa pemeriksaan.
                return validate_draft(self._deterministik(plan), plan, "writer-agent")
        return validate_draft(self._deterministik(plan), plan, "writer-agent")


# --------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    import sys

    from .planner import PlannerAgent

    sku = sys.argv[1] if len(sys.argv) > 1 else "AY-SR-101"
    plat = sys.argv[2] if len(sys.argv) > 2 else "tiktok"
    llm = LLMClient()
    planner = PlannerAgent(llm=llm)
    plan = planner(planner.brief, sku, plat)
    draf = WriterAgent(llm=llm)(plan)
    print(f"mode planner: {plan.mode} · panjang draf: {len(draf)} karakter")
    print("-" * 60)
    print(draf)
