"""
contract.py — bentuk data yang disepakati antara orkestrator, Planner, dan Writer.

Kenapa kontrak ditulis eksplisit, bukan diserahkan ke "asal jalan":
  Agent buatan orang lain (rekan tim) akan mengembalikan bentuk yang sedikit berbeda.
  Tanpa validasi, kesalahannya muncul jauh di dalam loop sebagai KeyError yang
  membingungkan. Dengan validasi, ia muncul di detik pertama dengan pesan yang
  menyebut field mana yang salah.

Yang divalidasi HANYA bentuk dan batas wajar — bukan kebenaran isi. Kebenaran isi
tetap urusan Reviewer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

PLATFORMS = ("tiktok", "instagram", "marketplace")

# Batas keras per platform (spesifikasi di dataset_c/platform_specs.md).
# Dipakai Writer untuk membatasi diri dan orkestrator untuk menolak draf mustahil.
BATAS = {
    "tiktok":      {"kata_maks": 175, "karakter_maks": 2200, "emoji_maks": 2},
    "instagram":   {"kata_maks": 400, "karakter_maks": 2200, "emoji_maks": 2},
    "marketplace": {"kata_maks": 300, "karakter_maks": 2000, "emoji_maks": 0},
}


class ContractError(ValueError):
    """Dilempar saat agent mengembalikan bentuk yang tidak sesuai kontrak."""

    def __init__(self, siapa: str, masalah: list[str]):
        self.siapa = siapa
        self.masalah = masalah
        super().__init__(f"{siapa} melanggar kontrak: " + "; ".join(masalah))


@dataclass
class Plan:
    """
    Rencana konten. Ini satu-satunya hal yang diterima Writer dari Planner.

    Sengaja TIDAK memuat rulebook. Writer tidak boleh menjadi pengawas
    kepatuhannya sendiri — ia hanya tahu fakta yang boleh dipakai dan yang dilarang.
    """

    sku: str
    platform: str
    angle: str                                  # sudut cerita, satu kalimat
    struktur: list[str]                         # urutan bagian, mis. HOOK/ISI/CTA
    fakta_boleh: list[str]                      # klaim yang diizinkan (dari lembar produk)
    fakta_dilarang: list[str]                   # klaim yang harus dihindari
    nama: str = ""                              # nama produk, diisi Planner dari registri
    kategori: str = ""                          # mis. "Serum wajah"
    harga: str = ""                             # harga normal, mis. "Rp149.000"
    harga_promo: str = ""                       # harga promo, kosong bila tidak ada
    bpom: str = ""                              # nomor notifikasi BPOM
    isi: str = ""                               # isi bersih, mis. "30 ml"
    disclaimer: str = "Hasil dapat berbeda pada setiap orang."
    emoji_maks: int = 2
    catatan: str = ""                           # arahan tambahan untuk Writer
    sumber: list[str] = field(default_factory=list)   # dokumen yang dipakai Planner
    pembuat: str = "planner-agent"              # siapa yang membuat rencana ini
    mode: str = "deterministik"                 # deterministik | llm | fallback

    # ---------------------------------------------------------------- konversi
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict, pembuat: str = "planner-agent") -> "Plan":
        """Bangun Plan dari JSON model. Field tak dikenal diabaikan, bukan meledak."""
        if not isinstance(d, dict):
            raise ContractError(pembuat, [f"rencana harus objek JSON, bukan {type(d).__name__}"])
        dikenal = {f for f in cls.__dataclass_fields__}
        bersih = {k: v for k, v in d.items() if k in dikenal}
        bersih.setdefault("pembuat", pembuat)
        wajib = ("sku", "platform", "angle", "struktur", "fakta_boleh", "fakta_dilarang")
        kurang = [f for f in wajib if f not in bersih]
        if kurang:
            raise ContractError(pembuat, [f"field wajib belum ada: {', '.join(kurang)}"])
        return cls(**bersih)

    # ---------------------------------------------------------------- validasi
    def validate(self, pembuat: str = "planner") -> list[str]:
        m: list[str] = []
        if not str(self.sku).strip():
            m.append("sku kosong")
        if self.platform not in PLATFORMS:
            m.append(f"platform '{self.platform}' tidak dikenal (pilihan: {', '.join(PLATFORMS)})")
        if not str(self.angle).strip():
            m.append("angle kosong — Writer tidak akan tahu harus menulis apa")
        if not isinstance(self.struktur, list) or not self.struktur:
            m.append("struktur harus daftar bagian yang tidak kosong")
        if not isinstance(self.fakta_boleh, list):
            m.append("fakta_boleh harus daftar")
        elif not self.fakta_boleh:
            m.append("fakta_boleh kosong — Writer dilarang mengarang fakta, jadi tidak bisa menulis")
        if not isinstance(self.fakta_dilarang, list):
            m.append("fakta_dilarang harus daftar")
        if not str(self.harga).strip():
            m.append("harga kosong — R-06 membutuhkan harga resmi")
        if not isinstance(self.emoji_maks, int) or self.emoji_maks < 0:
            m.append("emoji_maks harus bilangan bulat >= 0")
        elif self.emoji_maks > BATAS[self.platform]["emoji_maks"]:
            m.append(f"emoji_maks {self.emoji_maks} melebihi batas platform "
                     f"({BATAS[self.platform]['emoji_maks']})")
        return m


def validate_plan(plan, pembuat: str = "planner") -> Plan:
    """Pastikan apa pun yang dikembalikan agent benar-benar berbentuk Plan."""
    if isinstance(plan, dict):
        plan = Plan.from_dict(plan, pembuat=pembuat)
    if not isinstance(plan, Plan):
        raise ContractError(pembuat, [f"harus mengembalikan Plan atau dict, bukan {type(plan).__name__}"])
    m = plan.validate(pembuat)
    if m:
        raise ContractError(pembuat, m)
    return plan


# --------------------------------------------------------------------------- draf
FRONT_MATTER = ("---",)


def validate_draft(draft, plan: Plan, pembuat: str = "writer") -> str:
    """
    Periksa draf yang dikembalikan Writer.

    Yang ditolak di sini: bukan string, kosong, masih membawa front-matter YAML,
    atau melampaui batas platform. Semua itu membuat Reviewer bekerja pada input
    yang tidak sah — dan hasil review-nya jadi menyesatkan.
    """
    m: list[str] = []
    if not isinstance(draft, str):
        raise ContractError(pembuat, [f"draf harus string, bukan {type(draft).__name__}"])

    teks = draft.strip()
    if not teks:
        m.append("draf kosong")
    if teks.startswith("---"):
        m.append("draf masih memuat front-matter YAML (---); kirim isi konten saja")
    if len(teks) < 40:
        m.append(f"draf terlalu pendek ({len(teks)} karakter) untuk dinilai")

    batas = BATAS.get(plan.platform, BATAS["instagram"])
    kata = len(teks.split())
    if kata > batas["kata_maks"] * 2:
        m.append(f"draf {kata} kata, jauh di atas batas wajar platform "
                 f"({batas['kata_maks']}); kemungkinan mengembalikan penjelasan, bukan konten")

    if m:
        raise ContractError(pembuat, m)
    return teks


# --------------------------------------------------------------------------- util
def parse_json_loose(s: str) -> dict:
    """
    Ambil objek JSON dari keluaran model yang kadang menambahkan pagar ```json
    atau kalimat pembuka. Melempar ValueError bila benar-benar tidak ada JSON.
    """
    if not isinstance(s, str):
        raise ValueError("keluaran model bukan teks")
    t = s.strip()
    if t.startswith("```"):
        t = t.split("```")[1] if len(t.split("```")) > 1 else t
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    t = t.strip()
    if not t.startswith("{"):
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j < 0:
            raise ValueError("tidak ada objek JSON pada keluaran model")
        t = t[i:j + 1]
    return json.loads(t)
