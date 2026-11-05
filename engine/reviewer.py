"""
reviewer.py — Reviewer Agent untuk Challenge C (kosmetik).

Dua lapis, sengaja dipisah:

  LAPIS 1 — DETERMINISTIK (kode). Aturan yang bisa diperiksa tanpa selera:
      R-01/02 klaim terapeutik · R-03 klaim halal · R-06 angka · R-07 superlatif
      R-09 disclaimer · R-10 emoji · R-11 ketertelusuran · R-12 kompetitor
      R-13 pemutih · R-14 klaim absolut + batas platform
      R-16 izin edar/notifikasi · R-17 izin produksi · R-18 organik (USDA)
      R-19 uji dermatologis/SPF · R-20 bahasa klaim absolut · R-21 batas pengawet

  LAPIS 2 — PENILAIAN (model). Yang butuh pemahaman bahasa:
      nada merek, akurasi parafrase, risiko menyinggung.

Kedua lapis menulis ke format yang sama, dan SETIAP temuan wajib mengutip teks yang
benar-benar ada di draf. Kutipan yang tidak ditemukan dibuang — ini yang mencegah
Reviewer mengarang pelanggaran.

Aturan paling halus yang dijaga di sini:
    produk BELUM bersertifikat  -> bukan pelanggaran (kewajiban kosmetik 17 Okt 2028)
    produk MENKLAIM halal tanpa sertifikat -> pelanggaran (R-03)
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from governance import AuditLog

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "dataset_c"
AS_OF = date(2026, 10, 30)

RULEBOOK = {
    "R-01": "Kosmetik dilarang mengklaim menyembuhkan/mengobati",
    "R-02": "Kosmetik bukan obat; nomor BPOM wajib di marketplace",
    "R-03": "Klaim halal wajib nomor sertifikat yang berlaku dan mencakup produk",
    "R-04": "Klaim manfaat hanya yang ada di lembar produk",
    "R-05": "Testimoni bukan klaim produk",
    "R-06": "Angka harus persis sesuai lembar produk",
    "R-07": "Superlatif & janji hasil dilarang",
    "R-08": "Before-after menyesatkan dilarang",
    "R-09": "Klaim pencerahan wajib disclaimer",
    "R-10": "Nada merek; maksimal 2 emoji",
    "R-11": "Setiap fakta harus terlacak ke lembar produk",
    "R-12": "Tidak merendahkan kompetitor dengan nama",
    "R-13": "Dilarang 'memutihkan'/'whitening' — gunakan 'mencerahkan'",
    "R-14": "Dilarang klaim absolut (semua kulit, tanpa efek samping)",
    "R-15": "Bebas alkohol/babi tidak menggantikan sertifikat halal",
    "R-16": "Klaim terdaftar BPOM wajib nomor izin/notifikasi yang masih berlaku",
    "R-17": "Klaim pabrik tersertifikasi wajib izin produksi kategori yang berlaku",
    "R-18": "Klaim organik wajib sertifikat organik (USDA) yang berlaku",
    "R-19": "Klaim dermatologically tested/SPF wajib sertifikat uji yang berlaku",
    "R-20": "Produk belum teruji memakai 'membantu/mengurangi', bukan klaim absolut",
    "R-21": "Kadar pengawet tidak boleh melebihi batas; 'bebas pengawet' harus benar",
}

# frasa terlarang -> (aturan, label)
PROHIBITED = [
    (r"\bterbaik\b|\bajaib\b|\bmujarab\b", "R-07", "superlatif"),
    (r"\bnomor\s*1\b|\bno\.?\s*1\b", "R-07", "superlatif"),
    (r"\bdijamin\b", "R-07", "janji hasil"),
    (r"\bpasti\b", "R-07", "janji hasil"),
    (r"\binstan\b|\bseketika\b", "R-07", "janji hasil"),
    (r"\bpermanen\b", "R-07", "janji hasil"),
    (r"\bdalam\s+\d+\s*hari\b", "R-07", "janji waktu hasil"),
    (r"\b\d+\s*hari\s*(saja|langsung)\b", "R-07", "janji waktu hasil"),
    (r"\b(hilang|menghilang)\s+total\b", "R-07", "janji hasil"),

    (r"\bmemutihkan\b|\bpemutih\b|\bwhitening\b|\bmem\s*putih", "R-13", "klaim pemutihan"),

    (r"\bmengobati\b|\bmenyembuhkan\b|\bsembuh\w*\b|\bkesembuhan\b",
     "R-01", "klaim terapeutik"),
    (r"\bmengatasi\s+jerawat\b|\bobat\s+jerawat\b", "R-01", "klaim terapeutik"),
    (r"\bmenghilangkan\s+(bekas\s+luka|selulit|komedo)\b", "R-01", "klaim terapeutik"),
    (r"\banti[-\s]?inflamasi\b", "R-01", "klaim terapeutik"),

    (r"\bsemua\s+jenis\s+kulit\b|\bsemua\s+orang\b", "R-14", "klaim absolut"),
    (r"\btanpa\s+efek\s+samping\b", "R-14", "klaim absolut"),
    (r"\b100\s*%\s*aman\b|\bhypoallergenic\b", "R-14", "klaim absolut"),

    (r"\bkompetitor\b|\bserum\s+lain\b|\bproduk\s+lain\b|\bmerek\s+lain\b", "R-12", "menyinggung kompetitor"),
    (r"\btherapy\b|\btreatment\s+medis\b", "R-02", "posisi sebagai obat"),
    (r"\bobat\b", "R-02", "menyebut produk sebagai obat"),

    (r"\bpelanggan\s+kami\b|\bmenurut\s+pelanggan\b|\bkata\s+pelanggan\b|\btestimoni\b",
     "R-05", "testimoni dipakai sebagai klaim"),
    (r"\bsebelum\s*(dan|&|/)?\s*sesudah\b|\bbefore[\s-]*after\b|\bfoto\s+sebelum\b",
     "R-08", "before-after menyesatkan"),

    # klaim yang tidak tercantum di lembar produk (daftar terkurasi; cakupan penuh butuh lapis model)
    (r"\bbpa[\s-]*free\b", "R-04", "klaim tidak ada di lembar produk"),
    (r"\bvegan\b|\bcruelty[\s-]*free\b", "R-04", "klaim tidak ada di lembar produk"),
    (r"\bnon[\s-]*comedogenic\b", "R-04", "klaim tidak ada di lembar produk"),
    (r"\bhalal\s+mui\b", "R-03", "penerbit salah, sertifikat diterbitkan BPJPH"),

    (r"\bbebas\s+alkohol\b|\btanpa\s+babi\b|\bno\s*pork\b|\bpork\s*free\b", "R-15", "pengganti sertifikat"),
]

HALAL_RE = re.compile(r"\bhalal\b|#halal", re.I)
CERT_RE = re.compile(r"\bID\d{10,}\b")
DISCLAIMER_RE = re.compile(r"hasil\s+(dapat|bisa|mungkin)\s+berbeda", re.I)
BRIGHT_RE = re.compile(r"\bmencerahkan\b|\bcerah\b|\bglowing\b|\bbrightening\b", re.I)

# ---- legalitas & klaim khusus (R-16..R-21) --------------------------------
# Hanya memicu saat draf MENYATAKAN status, bukan sekadar menyebut nomor.
IZIN_EDAR_RE = re.compile(
    r"\b(terdaftar\s+(?:di\s+)?bpom|sudah\s+(?:terdaftar\s+)?bpom|"
    r"bpom\s+certified|certified\s+bpom|legal\s+bpom|resmi\s+bpom|"
    r"punya\s+izin\s+edar|izin\s+edar\s+(?:resmi|terbit))\b", re.I)

IZIN_PRODUKSI_RE = re.compile(
    r"\b(pabrik\s+(?:yang\s+)?(?:sudah\s+)?(?:tersertifikasi|bersertifikat)|"
    r"tersertifikasi\s+cpkb|cpkb|good\s+manufacturing\s+practice|gmp|"
    r"izin\s+produksi)\b", re.I)

ORGANIK_RE = re.compile(r"\b(organik|organic|usda)\b", re.I)

UJI_KLAIM_RE = re.compile(
    r"\b(dermatologically\s+tested|dermatologis\s+teruji|"
    r"telah\s+diuji\s+dermatologis|diuji\s+dermatologis)\b", re.I)
SPF_RE = re.compile(r"\b(spf\s*\d+|broad\s+spectrum)\b", re.I)

# R-20: bahasa absolut untuk produk yang belum diuji
KLAIM_ABSOLUT = [
    (r"\bmembunuh\s+(?:kuman|bakteri|virus|jamur)\b", "membunuh kuman"),
    (r"\bmembasmi\s+(?:kuman|bakteri|virus|jamur)\b", "membasmi kuman"),
    (r"\b100\s*%\s*(?:membunuh|menghilangkan|mematikan)\b", "klaim 100%"),
    (r"\bmenghilangkan\s+(?:kuman|bakteri|jerawat|noda)\b", "menghilangkan"),
]

# R-21: kadar pengawet yang disebut eksplisit di draf
KONSENTRASI_RE = re.compile(
    r"(phenoxyethanol|methylparaben|propylparaben|sodium\s+benzoate|"
    r"potassium\s+sorbate|chlorphenesin|dmdm\s+hydantoin)"
    r"\s*(?:sebanyak\s*)?(\d+(?:[.,]\d+)?)\s*%", re.I)

BEBAS_PENGAWET_RE = re.compile(
    r"\b(bebas\s+pengawet|tanpa\s+pengawet|preservative[\s-]*free)\b", re.I)
BEBAS_PARABEN_RE = re.compile(
    r"\b(bebas\s+paraben|tanpa\s+paraben|paraben[\s-]*free)\b", re.I)
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2B00-\u2BFF]"
)


def _rp(n: int) -> str:
    """149000 -> '149.000' (tanpa menyentuh tanda baca lain)."""
    return f"{n:,}".replace(",", ".")


def strip_markdown(t: str) -> str:
    """Hapus penanda ** dan __ serta komentar HTML supaya kutipan terbaca bersih."""
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)   # komentar penulis, bukan isi konten
    return re.sub(r"\*\*|__", "", t)


@dataclass
class Violation:
    rule_id: str
    span: str
    reason: str
    fix: str
    layer: str = "deterministik"

    def as_dict(self) -> dict:
        return {"rule_id": self.rule_id, "span": self.span,
                "reason": self.reason, "fix": self.fix, "layer": self.layer}


@dataclass
class ReviewResult:
    sku: str
    platform: str
    iteration: int
    verdict: str = "LOLOS"
    violations: list[Violation] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    dropped_llm: list[dict] = field(default_factory=list)
    catatan: list[str] = field(default_factory=list)

    def report(self) -> str:
        baris = [f"{self.sku} · {self.platform} · iterasi {self.iteration} → {self.verdict}"]
        if not self.violations:
            baris.append("  ✔ tidak ada pelanggaran")
        for c in self.catatan:
            baris.append(f"  ! {c}")
        for v in self.violations:
            baris.append(f"  ✗ {v.rule_id} [{v.layer}] “{v.span}”")
            baris.append(f"      alasan: {v.reason}")
            baris.append(f"      perbaiki: {v.fix}")
        return "\n".join(baris)


class Reviewer:
    def __init__(self, data_dir: Path = DATA, as_of: date = AS_OF, audit: AuditLog | None = None):
        self.data = data_dir
        self.as_of = as_of
        self.audit = audit or AuditLog()
        self.products = {r["sku"]: r for r in self._rows("products.csv")}
        self.certs = {r["cert_id"]: r for r in self._rows("certificates.csv")}
        self.sheets = {p.stem.split("_")[0]: p.read_text(encoding="utf-8")
                       for p in (self.data / "product_sheets").glob("PS-*.md")}
        self.sheet_by_sku = {}
        for r in self.products.values():
            for k, v in self.sheets.items():
                if f"sku: {r['sku']}" in v:
                    self.sheet_by_sku[r["sku"]] = v

        # ---- registri legalitas & komposisi (R-16..R-21) ----
        # Dibaca sebagai DATA, bukan ditanam di kode: menambah SKU atau mengubah
        # batas pengawet cukup mengubah CSV, tanpa menyentuh Reviewer.
        self.izin_edar = {r["sku"]: r for r in self._rows_safe("izin_edar.csv")}
        self.izin_produksi = {(r.get("kategori") or "").strip().lower(): r
                              for r in self._rows_safe("izin_produksi.csv")}
        self.sert_klaim = self._rows_safe("sertifikat_klaim.csv")
        self.batas_pengawet: dict[str, float] = {}
        for r in self._rows_safe("batas_pengawet.csv"):
            try:
                self.batas_pengawet[(r["nama_inci"] or "").strip().lower()] = \
                    float(r["batas_persen"])
            except (KeyError, ValueError):
                continue
        self.komposisi: dict[str, list[dict]] = {}
        for r in self._rows_safe("komposisi_produk.csv"):
            self.komposisi.setdefault(r["sku"], []).append(r)

    def _rows(self, name: str) -> list[dict]:
        # utf-8-sig: Excel di Windows menyimpan CSV dengan BOM, dan tanpa ini
        # nama kolom pertama menjadi "\ufeffsku" -> KeyError yang membingungkan.
        with open(self.data / name, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def _rows_safe(self, name: str) -> list[dict]:
        """Seperti _rows, tapi mengembalikan [] bila berkas belum ada."""
        p = self.data / name
        if not p.exists():
            return []
        with open(p, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    # ------------------------------------------------------------------ util
    BOUND = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"(])|\n+")

    @classmethod
    def _sentence_at(cls, text: str, idx: int) -> str:
        """
        Ambil kalimat yang memuat posisi idx — untuk kutipan yang bisa diverifikasi.
        Tidak memecah pada titik ribuan (Rp149.000); hanya pada titik yang diikuti
        spasi + huruf besar, atau pada baris baru.
        """
        bounds = [0] + [m.end() for m in cls.BOUND.finditer(text)] + [len(text)]
        for a, b in zip(bounds, bounds[1:]):
            if a <= idx < b:
                return cls._tidy(text[a:b])
        return cls._tidy(text[max(0, idx - 40):idx + 40])

    @staticmethod
    def _tidy(s: str, limit: int = 180) -> str:
        """Rapikan kutipan: baris baru jadi spasi, potong di batas kata + elipsis."""
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) <= limit:
            return s
        cut = s[:limit].rsplit(" ", 1)[0]
        return cut.rstrip(",.;:") + "…"

    def _cert_valid(self, sku: str) -> tuple[bool, str]:
        p = self.products[sku]
        cid = p.get("cert_id", "").strip()
        if not cid:
            return False, f"status {p['cert_status']}"
        c = self.certs.get(cid)
        if not c:
            return False, "sertifikat tidak ada di registri"
        if c["status"] != "AKTIF":
            return False, f"{cid} {c['status']} (s/d {c['berlaku_sampai']})"
        if sku not in c["sku_tercakup"].split(";"):
            return False, f"{cid} tidak mencakup {sku}"
        if date.fromisoformat(c["berlaku_sampai"]) < self.as_of:
            return False, f"{cid} kedaluwarsa {c['berlaku_sampai']}"
        return True, c["nomor"]

    # ------------------------------------------------------------------ LAPIS 1
    def _check_halal(self, text: str, sku: str) -> list[Violation]:
        """R-03. Klaim halal butuh sertifikat aktif + nomor + cakupan."""
        out = []
        for m in HALAL_RE.finditer(text):
            ok, info = self._cert_valid(sku)
            kutip = self._sentence_at(text, m.start())
            if not ok:
                out.append(Violation(
                    "R-03", kutip,
                    f"Klaim halal, tetapi produk belum punya sertifikat yang sah ({info}). "
                    f"Produk tanpa sertifikat bukan pelanggaran — mengklaimnya yang melanggar.",
                    "Hapus seluruh klaim halal (termasuk hashtag/emoji) sampai sertifikat terbit."))
            else:
                nums = CERT_RE.findall(text)
                if not nums:
                    out.append(Violation(
                        "R-03", kutip,
                        f"Klaim halal tanpa mencantumkan nomor sertifikat ({info}).",
                        f"Cantumkan nomor sertifikat {info}."))
                elif nums[0] != info:
                    out.append(Violation(
                        "R-03", kutip,
                        f"Nomor sertifikat di draf ({nums[0]}) tidak sesuai registri ({info}).",
                        f"Ganti dengan nomor yang benar: {info}."))
        return out

    # ------------------------------------------------- legalitas & klaim (R-16..R-21)
    def _berlaku(self, row: dict) -> bool:
        """Status AKTIF dan tanggal berlaku belum lewat (as_of)."""
        if (row.get("status") or "").strip().upper() != "AKTIF":
            return False
        try:
            return date.fromisoformat(row["berlaku_sampai"]) >= self.as_of
        except (KeyError, ValueError):
            return False

    def _sert_klaim_valid(self, sku: str, jenis: str) -> tuple[bool, str]:
        kandidat = [r for r in self.sert_klaim
                    if r.get("sku_tercakup") == sku and r.get("jenis") == jenis]
        if not kandidat:
            return False, f"tidak ada sertifikat {jenis} untuk {sku}"
        for r in kandidat:
            if self._berlaku(r):
                return True, r.get("nomor", "")
        r = kandidat[0]
        return False, (f"{r.get('cert_id')} {r.get('status')} "
                       f"(s/d {r.get('berlaku_sampai')})")

    def _check_izin_edar(self, text: str, sku: str) -> list[Violation]:
        """R-16. Klaim 'terdaftar/sudah BPOM' butuh notifikasi/izin edar yang berlaku."""
        out = []
        for m in IZIN_EDAR_RE.finditer(text):
            row = self.izin_edar.get(sku)
            kutip = self._sentence_at(text, m.start())
            if row is None:
                out.append(Violation(
                    "R-16", kutip,
                    "Klaim terdaftar BPOM, tetapi SKU ini tidak punya nomor "
                    "notifikasi/izin edar di registri.",
                    "Hapus klaim status; cantumkan nomor setelah notifikasi terbit."))
            elif not self._berlaku(row):
                out.append(Violation(
                    "R-16", kutip,
                    f"Klaim terdaftar BPOM, tetapi notifikasi {row.get('nomor')} "
                    f"{row.get('status')} (s/d {row.get('berlaku_sampai')}).",
                    "Hapus klaim status sampai notifikasi diperpanjang."))
        return out

    def _check_izin_produksi(self, text: str, sku: str) -> list[Violation]:
        """R-17. Klaim pabrik tersertifikasi butuh izin produksi kategori yang berlaku."""
        out = []
        kategori = (self.products[sku].get("kategori") or "").strip().lower()
        row = self.izin_produksi.get(kategori)
        for m in IZIN_PRODUKSI_RE.finditer(text):
            kutip = self._sentence_at(text, m.start())
            if row is None:
                out.append(Violation(
                    "R-17", kutip,
                    f"Klaim izin produksi, tetapi kategori '{kategori}' belum punya "
                    f"izin produksi di registri.",
                    "Hapus klaim pabrik tersertifikasi."))
            elif not self._berlaku(row):
                out.append(Violation(
                    "R-17", kutip,
                    f"Klaim pabrik tersertifikasi, tetapi izin produksi kategori "
                    f"'{kategori}' {row.get('status')} (s/d {row.get('berlaku_sampai')}).",
                    "Hapus klaim sampai izin produksi diperpanjang."))
        return out

    def _check_klaim_khusus(self, text: str, sku: str) -> list[Violation]:
        """R-18 organik/USDA · R-19 dermatologically tested/SPF."""
        out = []
        for m in ORGANIK_RE.finditer(text):
            ok, info = self._sert_klaim_valid(sku, "USDA_ORGANIC")
            if not ok:
                out.append(Violation(
                    "R-18", self._sentence_at(text, m.start()),
                    f"Klaim organik, tetapi {info}.",
                    "Hapus klaim organik; sertifikat harus berlaku dan mencakup produk."))
        for m in UJI_KLAIM_RE.finditer(text):
            ok, info = self._sert_klaim_valid(sku, "DERMATOLOGICALLY_TESTED")
            if not ok:
                out.append(Violation(
                    "R-19", self._sentence_at(text, m.start()),
                    f"Klaim uji dermatologis, tetapi {info}.",
                    "Hapus klaim uji; cantumkan nomor laporan uji bila ada."))
        for m in SPF_RE.finditer(text):
            ok, info = self._sert_klaim_valid(sku, "SPF_TEST")
            if not ok:
                out.append(Violation(
                    "R-19", self._sentence_at(text, m.start()),
                    f"Klaim SPF, tetapi {info}.",
                    "Hapus klaim SPF; produk ini bukan sunscreen dan tidak punya uji SPF."))
        return out

    def _check_bahasa_klaim(self, text: str) -> list[Violation]:
        """R-20. Produk belum teruji: 'membantu/mengurangi', bukan klaim absolut."""
        out, seen = [], set()
        for pat, label in KLAIM_ABSOLUT:
            for m in re.finditer(pat, text, re.I):
                kunci = m.group(0).lower()
                if kunci in seen:
                    continue
                seen.add(kunci)
                out.append(Violation(
                    "R-20", self._sentence_at(text, m.start()),
                    f"{label}: “{m.group(0)}” adalah klaim absolut untuk produk "
                    f"yang belum diuji.",
                    "Gunakan bahasa berhati-hati: 'membantu', 'mengurangi', "
                    "'dapat membantu'."))
        return out

    def _check_pengawet(self, text: str, sku: str) -> list[Violation]:
        """R-21. Kadar pengawet di draf harus di bawah batas; klaim 'bebas' harus benar."""
        out = []
        for m in KONSENTRASI_RE.finditer(text):
            nama = re.sub(r"\s+", " ", m.group(1)).strip().lower()
            try:
                kadar = float(m.group(2).replace(",", "."))
            except ValueError:
                continue
            batas = self.batas_pengawet.get(nama)
            if batas is not None and kadar > batas:
                out.append(Violation(
                    "R-21", self._sentence_at(text, m.start()),
                    f"Kadar {m.group(1)} {kadar:g}% melebihi batas {batas:g}%.",
                    f"Turunkan ke maksimal {batas:g}% atau hapus angka kadarnya."))

        komposisi = self.komposisi.get(sku, [])
        ada_pengawet = any((r.get("fungsi") or "").strip().lower() == "pengawet"
                           for r in komposisi)
        ada_paraben = any("paraben" in (r.get("bahan_inci") or "").lower()
                          for r in komposisi)

        for m in BEBAS_PENGAWET_RE.finditer(text):
            if ada_pengawet:
                out.append(Violation(
                    "R-21", self._sentence_at(text, m.start()),
                    "Klaim bebas pengawet, tetapi komposisi memuat pengawet.",
                    "Hapus klaim bebas pengawet."))
        for m in BEBAS_PARABEN_RE.finditer(text):
            if ada_paraben:
                out.append(Violation(
                    "R-21", self._sentence_at(text, m.start()),
                    "Klaim bebas paraben, tetapi komposisi memuat paraben.",
                    "Hapus klaim bebas paraben."))
        return out

    def audit_komposisi(self, sku: str) -> list[dict]:
        """
        Periksa komposisi produk terhadap batas pengawet (R-21).

        Dipakai layer reviewer AWAL: sebelum konten ditulis, kemasan dan komposisi
        diperiksa dulu. Mengembalikan daftar masalah (bukan Violation) karena tidak
        ada kutipan draf yang bisa diambil.
        """
        masalah: list[dict] = []
        total_paraben = 0.0
        for r in self.komposisi.get(sku, []):
            nama = (r.get("bahan_inci") or "").strip()
            fungsi = (r.get("fungsi") or "").strip().lower()
            kadar_raw = (r.get("kadar_persen") or "").strip()
            if not kadar_raw:
                continue
            try:
                kadar = float(kadar_raw.replace(",", "."))
            except ValueError:
                continue
            if fungsi != "pengawet":
                continue
            batas = self.batas_pengawet.get(nama.lower())
            if batas is not None and kadar > batas:
                masalah.append({"rule_id": "R-21", "bahan": nama, "kadar": kadar,
                                "batas": batas,
                                "alasan": f"{nama} {kadar:g}% melebihi batas {batas:g}%"})
            if "paraben" in nama.lower():
                total_paraben += kadar
        if total_paraben > 0.8:
            masalah.append({"rule_id": "R-21", "bahan": "Total paraben",
                            "kadar": round(total_paraben, 3), "batas": 0.8,
                            "alasan": f"Total paraben {total_paraben:g}% melebihi batas 0,8%"})
        return masalah

    def _check_prohibited(self, text: str) -> list[Violation]:
        """R-01/02/07/12/13/14/15 — daftar frasa terlarang."""
        out, seen = [], set()
        for pat, rule, label in PROHIBITED:
            for m in re.finditer(pat, text, re.I):
                kunci = (rule, m.group(0).lower())
                if kunci in seen:
                    continue
                seen.add(kunci)
                kutip = re.sub(r"\s+", " ", m.group(0))
                out.append(Violation(
                    rule, self._sentence_at(text, m.start()),
                    f"{label}: “{kutip}” melanggar {rule} — {RULEBOOK[rule]}.",
                    self._fix_hint(rule)))
        return out

    @staticmethod
    def _fix_hint(rule: str) -> str:
        return {
            "R-07": "Hapus janji hasil. Ganti dengan klaim yang ada di lembar produk.",
            "R-13": "Gunakan 'mencerahkan', bukan 'memutihkan'.",
            "R-01": "Hapus klaim terapeutik; kosmetik tidak mengobati.",
            "R-14": "Ganti dengan pernyataan bersyarat, mis. 'dirancang untuk kulit kusam'.",
            "R-12": "Hapus perbandingan dengan kompetitor.",
            "R-15": "Hapus; hanya sertifikat halal yang sah sebagai dasar klaim.",
            "R-02": "Hapus posisi sebagai obat.",
            "R-16": "Hapus klaim status BPOM sampai notifikasi/izin edar berlaku.",
            "R-17": "Hapus klaim pabrik tersertifikasi; izin produksi kategori belum berlaku.",
            "R-18": "Hapus klaim organik; butuh sertifikat organik yang berlaku.",
            "R-19": "Hapus klaim uji dermatologis/SPF; butuh laporan uji yang berlaku.",
            "R-20": "Gunakan 'membantu'/'mengurangi', bukan klaim absolut.",
            "R-21": "Sesuaikan kadar pengawet dengan batas; perbaiki klaim 'bebas'.",
        }.get(rule, "Perbaiki sesuai rulebook.")

    def _check_numbers(self, text: str, sku: str) -> list[Violation]:
        """R-06. Harga, isi bersih, nomor BPOM harus persis."""
        p = self.products[sku]
        out = []
        harga = int(p["harga"])
        promo = int(p["harga_promo"]) if p.get("harga_promo") else None

        for m in re.finditer(r"Rp\s*([\d.]+)", text):
            nilai = int(m.group(1).replace(".", ""))
            # konteks LOKAL (30 karakter sebelum angka), bukan seluruh kalimat —
            # satu kalimat bisa memuat harga promo DAN harga normal sekaligus.
            pre = text[max(0, m.start() - 30):m.start()].lower()
            if "normal" in pre or "resmi" in pre:
                if nilai != harga:
                    out.append(Violation(
                        "R-06", self._sentence_at(text, m.start()),
                        f"Harga normal disebut Rp{_rp(nilai)}, padahal Rp{_rp(harga)}.",
                        f"Tulis Rp{_rp(harga)} sebagai harga normal."))
            elif "promo" in pre or "peluncuran" in pre:
                if promo and nilai != promo:
                    out.append(Violation(
                        "R-06", self._sentence_at(text, m.start()),
                        f"Harga promo disebut Rp{_rp(nilai)}, padahal promo resmi Rp{_rp(promo)}.",
                        f"Tulis Rp{_rp(promo)} untuk harga promo."))

        # isi bersih
        for m in re.finditer(r"(\d+)\s*(ml|g)\b", text, re.I):
            satuan = m.group(2).lower()
            if satuan in p["isi"].lower() and int(m.group(1)) != int(re.sub(r"\D", "", p["isi"])):
                out.append(Violation(
                    "R-06", self._sentence_at(text, m.start()),
                    f"Isi disebut {m.group(0)}, padahal {p['isi']}.",
                    f"Tulis {p['isi']}."))

        # kuota promo: angka ketersediaan harus sama dengan yang terdaftar.
        # Tanpa ini, "kuota hanya 5 kursi" lolos karena tidak ada harga yang bisa
        # dibandingkan — angka ketersediaan bukan harga, tapi tetap klaim.
        kuota = (p.get("kuota_promo") or "").strip()
        for m in re.finditer(r"(\d+)\s*(pembeli|kursi|slot|kuota|unit|pcs)\b", text, re.I):
            n = int(m.group(1))
            if not kuota:
                out.append(Violation(
                    "R-07", self._sentence_at(text, m.start()),
                    f"Kuota {n} {m.group(2)} disebut, padahal tidak ada kuota promo terdaftar "
                    f"untuk produk ini.",
                    "Hapus angka kuota; jangan menyatakan ketersediaan tanpa dasar."))
            elif n != int(kuota):
                out.append(Violation(
                    "R-07", self._sentence_at(text, m.start()),
                    f"Kuota disebut {n} {m.group(2)}, padahal kuota resmi {kuota}.",
                    f"Tulis {kuota} atau hapus angka kuota."))

        # nomor BPOM
        bpom = re.findall(r"\bNA\d{8,}\b", text)
        for b in bpom:
            if b != p["notifikasi_bpom"]:
                out.append(Violation(
                    "R-06", b, f"Nomor BPOM {b} tidak sesuai ({p['notifikasi_bpom']}).",
                    f"Ganti dengan {p['notifikasi_bpom']}."))
        return out

    def _check_disclaimer(self, text: str) -> list[Violation]:
        """R-09. Klaim pencerahan wajib disclaimer."""
        m = BRIGHT_RE.search(text)
        if m and not DISCLAIMER_RE.search(text):
            return [Violation(
                "R-09", self._sentence_at(text, m.start()),
                "Ada klaim pencerahan tanpa disclaimer hasil.",
                "Tambahkan: 'Hasil dapat berbeda pada setiap orang.'")]
        return []

    def _check_emoji(self, text: str) -> list[Violation]:
        n = len(EMOJI_RE.findall(text))
        if n > 2:
            return [Violation("R-10", f"{n} emoji",
                              f"Draf memakai {n} emoji, batas 2 (R-10).",
                              "Kurangi menjadi maksimal 2 emoji.")]
        return []

    def _check_traceability(self, text: str, sku: str) -> list[Violation]:
        """R-11. Persentase bahan harus ada di lembar produk."""
        sheet = self.sheet_by_sku.get(sku, "")
        out = []
        for m in re.finditer(r"(\d+)\s*%", text):
            if f"{m.group(1)}%" not in sheet.replace(" ", ""):
                out.append(Violation(
                    "R-11", self._sentence_at(text, m.start()),
                    f"Angka {m.group(1)}% tidak ditemukan di lembar produk.",
                    "Hapus atau ganti dengan kadar yang tercantum di lembar produk."))
        return out

    def _check_platform(self, text: str, platform: str, sku: str) -> list[Violation]:
        out = []
        p = platform.lower()
        if p == "tiktok":
            kata = len(re.findall(r"\w+", text))
            if kata > 175:
                out.append(Violation("R-06", f"{kata} kata",
                                     f"Naskah {kata} kata, batas ±150 (spesifikasi TikTok).",
                                     "Pangkas naskah."))
        elif p == "instagram":
            if len(text) > 2200:
                out.append(Violation("R-06", f"{len(text)} karakter",
                                     "Caption melebihi 2200 karakter.",
                                     "Pangkas caption."))
            tags = re.findall(r"#\w+", text)
            if len(tags) > 30:
                out.append(Violation("R-06", f"{len(tags)} hashtag",
                                     "Hashtag melebihi 30.", "Kurangi hashtag."))
            for t in tags:
                if re.search(r"halal|pemutih|whitening", t, re.I):
                    out.append(Violation("R-03", t,
                                         f"Hashtag {t} adalah klaim.",
                                         "Hapus hashtag berklaim."))
        elif p in ("marketplace", "shopee", "tokopedia"):
            # SKU tak dikenal tidak punya nomor BPOM: lewati, jangan crash.
            produk = self.products.get(sku) or {}
            bpom = produk.get("notifikasi_bpom", "")
            if bpom and bpom not in text:
                out.append(Violation("R-02", "(tidak ada nomor BPOM)",
                                     "Listing marketplace wajib mencantumkan nomor BPOM.",
                                     f"Tambahkan nomor {bpom}."))
            # batas judul (spesifikasi marketplace): <=70 karakter, tanpa emoji
            m = re.search(r"(?:judul|title)\s*:\s*(.+)", text, re.I)
            if m:
                judul = m.group(1).strip()
                if len(judul) > 70:
                    out.append(Violation("R-06", judul[:70],
                                         f"Judul {len(judul)} karakter, batas 70.",
                                         "Pangkas judul."))
                if EMOJI_RE.search(judul):
                    out.append(Violation("R-10", judul,
                                         "Judul marketplace tidak boleh memuat emoji.",
                                         "Hapus emoji dari judul."))
        return out

    # ------------------------------------------------------------------ lintas platform
    def check_cross_platform(self, drafts: dict[str, str], sku: str) -> list[Violation]:
        """
        R-06: fakta yang sama tidak boleh berbeda antar platform.
        (Padanan kasus cadangan C-B5: dua platform menyebut harga berbeda untuk produk sama.)
        """
        nilai: dict[str, set[int]] = {}
        for platform, teks in drafts.items():
            for m in re.finditer(r"Rp\s*([\d.]+)", teks):
                nilai.setdefault(platform, set()).add(int(m.group(1).replace(".", "")))
        if len(nilai) < 2:
            return []

        semua = set().union(*nilai.values())
        if len(semua) <= 1:
            return []

        out = []
        acuan_platform, acuan = next(iter(nilai.items()))
        for platform, v in nilai.items():
            if platform == acuan_platform:
                continue
            beda = v.symmetric_difference(acuan)
            if beda:
                out.append(Violation(
                    "R-06", f"{platform}: {sorted(v)} vs {acuan_platform}: {sorted(acuan)}",
                    f"Harga berbeda antar platform ({', '.join(f'Rp{_rp(x)}' for x in sorted(beda))}).",
                    "Samakan angka di semua platform sesuai lembar produk."))
        return out

    # ------------------------------------------------------------------ LAPIS 2
    LLM_PROMPT = """Kamu Reviewer konten kosmetik. Nilai draf terhadap rulebook R-01..R-21.
Kembalikan JSON: {"findings":[{"rule_id":"R-xx","span":"<kutipan PERSIS dari draf>",
"reason":"...","fix":"..."}]}

Aturan mutlak:
- `span` HARUS disalin persis dari draf, karakter demi karakter. Temuan dengan kutipan
  yang tidak ditemukan akan dibuang otomatis.
- Fokus hanya pada yang butuh pemahaman bahasa: nada merek, akurasi parafrase,
  risiko menyinggung. Jangan ulangi hal yang sudah dicek kode (angka, frasa terlarang).
- Jika tidak ada temuan, kembalikan {"findings":[]}.
"""

    def apply_llm_findings(self, draft: str, findings: list[dict]) -> tuple[list[Violation], list[dict]]:
        """
        Terima temuan lapis-2 dari model, lalu VERIFIKASI.
        Temuan yang kutipannya tidak ada di draf dibuang — ini penjaga anti-halusinasi.
        """
        accepted, dropped = [], []
        for f in findings:
            span = (f.get("span") or "").strip()
            rid = f.get("rule_id", "")
            if rid not in RULEBOOK:
                dropped.append({**f, "alasan_tolak": "rule_id tidak dikenal"})
                continue
            if not span or span not in draft:
                dropped.append({**f, "alasan_tolak": "kutipan tidak ditemukan di draf"})
                continue
            accepted.append(Violation(rid, span, f.get("reason", ""), f.get("fix", ""), "llm"))
        return accepted, dropped

    # ------------------------------------------------------------------ utama
    def review(self, draft: str, sku: str, platform: str, iteration: int = 1,
               llm_findings: list[dict] | None = None, actor: str = "reviewer-agent",
               log: bool = True) -> ReviewResult:
        """
        Jalankan lapis-1 (+ lapis-2 bila `llm_findings` diberikan).

        `log=False` dipakai untuk review sementara: hasil deterministik dipakai
        untuk menyusun prompt lapis-2, dan yang dicatat ke audit hanya verdict final.
        Tanpa ini, satu iterasi menghasilkan dua entri audit yang membingungkan.
        """
        # SKU yang tidak ada di registri TIDAK boleh menjatuhkan proses.
        # Di Demo Day, juri bisa memberi draf untuk produk yang belum terdaftar.
        # Perilaku yang benar: jalankan pemeriksaan teks, lewati pemeriksaan yang
        # butuh data produk, dan nyatakan keterbatasannya — bukan crash, dan
        # bukan "LOLOS" yang memberi rasa aman palsu.
        dikenal = sku in self.products
        res = ReviewResult(sku, platform, iteration)

        checks = [
            ("R-20 bahasa klaim", self._check_bahasa_klaim(draft)),
            ("R-21 pengawet", self._check_pengawet(draft, sku)),
            ("R-01/02/07/12/13/14/15 frasa terlarang", self._check_prohibited(draft)),
            ("R-09 disclaimer", self._check_disclaimer(draft)),
            ("R-10 emoji", self._check_emoji(draft)),
            ("spesifikasi platform", self._check_platform(draft, platform, sku)),
        ]
        if dikenal:
            checks = [
                ("R-03 klaim halal", self._check_halal(draft, sku)),
                ("R-16 izin edar", self._check_izin_edar(draft, sku)),
                ("R-17 izin produksi", self._check_izin_produksi(draft, sku)),
                ("R-18/19 klaim khusus", self._check_klaim_khusus(draft, sku)),
                ("R-06 angka", self._check_numbers(draft, sku)),
                ("R-11 ketertelusuran", self._check_traceability(draft, sku)),
            ] + checks
        else:
            res.catatan.append(
                f"SKU {sku} tidak ada di registri: harga, nomor BPOM, halal, izin, "
                f"dan klaim khusus tidak dapat diverifikasi.")
        for nama, hasil in checks:
            res.checks.append(nama)
            res.violations.extend(hasil)

        if llm_findings:
            acc, drop = self.apply_llm_findings(draft, llm_findings)
            res.violations.extend(acc)
            res.dropped_llm = drop
            res.checks.append("lapis-2 penilaian model")

        # dedupe (aturan + kutipan sama)
        seen, uniq = set(), []
        for v in res.violations:
            k = (v.rule_id, v.span, v.reason)
            if k not in seen:
                seen.add(k)
                uniq.append(v)

        # dedupe lanjutan: untuk aturan sama, buang kutipan yang termuat di kutipan lain
        # (mis. '#halal' tertangkap dua kali: sebagai klaim halal dan sebagai hashtag)
        final: list[Violation] = []
        for v in uniq:
            if any(o.rule_id == v.rule_id and v.span != o.span and v.span in o.span
                   for o in uniq):
                continue
            final.append(v)
        res.violations = final
        if dikenal:
            res.verdict = "LOLOS" if not res.violations else "TOLAK"
        else:
            # Tanpa data produk, "LOLOS" akan jadi jaminan palsu.
            res.verdict = "TOLAK" if res.violations else "PERLU_DATA"

        if log:
            self.audit.append(
                actor, "review", f"{sku}/{platform}", res.verdict,
                evidence=[v.rule_id for v in res.violations],
                meta={"iterasi": iteration, "jumlah_temuan": len(res.violations),
                      "lapis2": bool(llm_findings), "dibuang_llm": len(res.dropped_llm)})
        return res

    # ------------------------------------------------------------------ verifikasi eksternal
    def verify_external(self, nomor: str) -> dict:
        """
        Cek nomor sertifikat ke registri publik BPJPH (bpjph.halal.go.id).

        Ini BUKAN penentu status produk internal — dipakai untuk:
          (a) membuktikan nomor yang diklaim memang ada,
          (b) audit saat ada nomor asing masuk lewat email/klaim pemasok.

        Catatan: produk di dataset_c memakai nomor MOCK, jadi tidak akan ditemukan
        di sini. Itu wajar dan justru dipakai untuk demo "nomor palsu tidak lolos".
        """
        try:
            from bpjph_client import cari_full
        except ImportError:
            return {"error": "bpjph_client tidak tersedia"}

        rows, meta = cari_full(no_regis=nomor, max_page=1)
        self.audit.append("reviewer-agent", "verify_external", nomor,
                          "DITEMUKAN" if rows else "TIDAK_DITEMUKAN",
                          evidence=[r["nama_produk"] for r in rows[:3]])
        return {
            "nomor": nomor,
            "ditemukan": bool(rows),
            "jumlah_produk_tercakup": meta.get("totalItems", 0),
            "contoh_produk": [{"nama": r["nama_produk"], "merek": r["merek"][:60],
                               "pelaku_usaha": r["pelaku_usaha"]} for r in rows[:3]],
            "sumber": "bpjph.halal.go.id/cari/sertifikat",
        }

    # ------------------------------------------------------------------ kendali loop
    MAX_ITERASI = 3

    def decide_next(self, res: ReviewResult) -> dict:
        """
        Keputusan setelah satu putaran review — ini yang menghentikan loop.
        Tanpa ini, agent bisa berputar tanpa henti (dilarang handbook).
        """
        if res.verdict == "LOLOS":
            return {"aksi": "SELESAI", "alasan": "semua aturan terpenuhi",
                    "lanjut_ke": "persetujuan manusia"}
        if res.iteration >= self.MAX_ITERASI:
            return {"aksi": "ESKALASI",
                    "alasan": f"iterasi {res.iteration} mencapai batas {self.MAX_ITERASI}",
                    "lanjut_ke": "manusia (Halal/Regulatory) + riwayat revisi",
                    "sisa_masalah": sorted({v.rule_id for v in res.violations})}
        return {"aksi": "REVISI", "alasan": f"{len(res.violations)} temuan",
                "lanjut_ke": f"Writer (iterasi {res.iteration + 1})"}


# --------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("pakai: python reviewer.py <file_draf.md> <SKU> [platform] [iterasi]")
        print("       python reviewer.py verify <nomor_sertifikat>")
        print("contoh: python reviewer.py ../dataset_c/sample_drafts/DRAFT-101_v1.md AY-SR-101 tiktok 1")
        sys.exit(0)

    if sys.argv[1] == "verify":
        import json
        print(json.dumps(Reviewer().verify_external(sys.argv[2]), ensure_ascii=False, indent=2))
        sys.exit(0)

    path, sku = sys.argv[1], sys.argv[2]
    plat = sys.argv[3] if len(sys.argv) > 3 else "tiktok"
    it = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    teks = Path(path).read_text(encoding="utf-8")
    teks = re.sub(r"^---.*?---", "", teks, flags=re.S)      # buang front-matter
    teks = strip_markdown(teks)

    r = Reviewer().review(teks, sku, plat, it)
    print(r.report())
    print(f"\n{len(r.checks)} pemeriksaan dijalankan · {len(r.violations)} temuan")
