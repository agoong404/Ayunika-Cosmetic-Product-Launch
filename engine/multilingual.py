"""
multilingual.py — tiga versi bahasa (ID / EN / ZH) dengan konsistensi fakta (C-15).

PENTING, baca sebelum mengklaim apa pun:
  Ini BUKAN mesin penerjemah dan BUKAN generator konten bebas. Yang ada di sini
  adalah kamus fakta kanonik (`dataset_c/multilingual/facts.json`) yang sudah
  ditulis dalam tiga bahasa, plus pemeriksa yang memastikan ketiga versi memuat
  **himpunan fakta yang sama**. Angka, kadar, isi, dan nomor BPOM sengaja tidak
  pernah diterjemahkan: nilainya identik di ketiga bahasa, sehingga penyimpangan
  bisa dideteksi secara deterministik.

Yang benar-benar dibuktikan modul ini:
  - setiap fakta kanonik (F-xx) hadir di ketiga versi;
  - token fakta (harga, kadar, isi, BPOM, sertifikat) identik di ketiga versi;
  - tidak ada klaim terlarang dalam bahasa masing-masing;
  - disclaimer wajib hadir dalam bahasa masing-masing.

Yang TIDAK dibuktikan: kualitas terjemahan, nada merek, atau kepatuhan hukum
terjemahan. Itu tetap butuh peninjauan manusia.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FAKTA = BASE / "dataset_c" / "multilingual" / "facts.json"
BAHASA = ("id", "en", "zh")

# Token yang tidak boleh berubah antar bahasa: harga, persen, isi, kode registri.
_POLA_TOKEN = re.compile(
    r"Rp\s?\d[\d.]*|\bNA\d{8,}\b|\bID\d{10,}\b|\d+(?:[.,]\d+)?\s?%|\d+\s?(?:ml|g)\b",
    re.IGNORECASE,
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"\s+", "", s)


def muat() -> dict:
    return json.loads(FAKTA.read_text(encoding="utf-8"))


def daftar_sku() -> list[str]:
    return sorted(muat()["sku"])


def fakta_sku(sku: str) -> dict | None:
    return muat()["sku"].get(sku)


def token_dari(teks: str) -> set[str]:
    """Ambil token fakta dari sebuah teks, ternormalisasi."""
    return {_norm(m.group(0)) for m in _POLA_TOKEN.finditer(str(teks))}


def versi_kanonik(sku: str, bahasa: str) -> dict:
    """
    Susun lembar fakta untuk satu bahasa dari kamus kanonik.

    Deterministik, tanpa model. Kode F-xx disisipkan sebagai penanda agar
    pemeriksa bisa membuktikan himpunan fakta identik lintas bahasa.
    """
    if bahasa not in BAHASA:
        return {"ok": False, "error": "bahasa_tidak_dikenal",
                "pesan": f"bahasa harus salah satu dari {', '.join(BAHASA)}"}
    data = fakta_sku(sku)
    if not data:
        return {"ok": False, "error": "sku_tidak_dikenal",
                "pesan": f"SKU {sku} tidak ada di kamus fakta. Jangan mengarang fakta."}

    baris = [f"# {data['nama'][bahasa]}"]
    for f in data["fakta"]:
        baris.append(f"[{f['kode']}] {f[bahasa]}")
    baris.append(f"[D-01] {data['disclaimer'][bahasa]}")
    return {"ok": True, "sku": sku, "bahasa": bahasa,
            "teks": "\n".join(baris),
            "kode_fakta": [f["kode"] for f in data["fakta"]] + ["D-01"],
            "catatan": "Lembar fakta terstruktur dari kamus kanonik, bukan terjemahan model."}


def cek_konsistensi(sku: str, versi: dict[str, str]) -> dict:
    """
    Bandingkan versi ID/EN/ZH terhadap kamus kanonik dan satu sama lain.

    `versi` = {"id": "...", "en": "...", "zh": "..."}.
    Mengembalikan `konsisten`, temuan per bahasa, dan ringkasan. Gagal tertutup:
    bahasa yang hilang atau SKU asing langsung dianggap tidak konsisten.
    """
    data = fakta_sku(sku)
    if not data:
        return {"ok": False, "error": "sku_tidak_dikenal", "konsisten": False,
                "pesan": "SKU tidak ada di kamus fakta — tidak ada yang bisa diverifikasi."}

    temuan: list[dict] = []
    per_bahasa: dict[str, dict] = {}
    himpunan_kode: dict[str, set[str]] = {}
    himpunan_token: dict[str, set[str]] = {}

    for b in BAHASA:
        teks = versi.get(b)
        if not isinstance(teks, str) or not teks.strip():
            temuan.append({"bahasa": b, "jenis": "versi_hilang",
                           "pesan": f"Versi '{b}' tidak ada atau kosong."})
            per_bahasa[b] = {"hadir": False, "kode": [], "token": []}
            himpunan_kode[b], himpunan_token[b] = set(), set()
            continue

        kode = set(re.findall(r"\[(F-\d+|D-01)\]", teks))
        token = token_dari(teks)
        himpunan_kode[b], himpunan_token[b] = kode, token
        per_bahasa[b] = {"hadir": True, "kode": sorted(kode), "token": sorted(token)}

        # 1. Fakta kanonik yang hilang
        harapan = {f["kode"] for f in data["fakta"]} | {"D-01"}
        for k in sorted(harapan - kode):
            temuan.append({"bahasa": b, "jenis": "fakta_hilang",
                           "pesan": f"{k} tidak ada di versi '{b}'."})
        # 2. Kode yang tidak dikenal (mengarang fakta)
        for k in sorted(kode - harapan):
            temuan.append({"bahasa": b, "jenis": "fakta_asing",
                           "pesan": f"{k} tidak dikenal di kamus untuk {sku}."})
        # 3. Token angka/kode yang tidak ada di kamus → potensi drift fakta
        token_sah = {_norm(t) for t in data["token"]}
        for t in sorted(token - token_sah):
            temuan.append({"bahasa": b, "jenis": "angka_asing",
                           "pesan": f"Token '{t}' tidak ada di registri {sku}."})
        # 4. Klaim terlarang per bahasa
        for kata in data["larangan"][b]:
            if _norm(kata) in _norm(teks):
                temuan.append({"bahasa": b, "jenis": "klaim_terlarang",
                               "pesan": f"Klaim terlarang '{kata}' muncul di versi '{b}'."})
        # 5. Disclaimer
        if _norm(data["disclaimer"][b]) not in _norm(teks):
            temuan.append({"bahasa": b, "jenis": "disclaimer_hilang",
                           "pesan": f"Disclaimer wajib tidak ada di versi '{b}'."})

    # 6. Himpunan fakta dan token harus identik lintas bahasa
    if all(per_bahasa[b]["hadir"] for b in BAHASA):
        dasar_kode, dasar_token = himpunan_kode["id"], himpunan_token["id"]
        for b in ("en", "zh"):
            for k in sorted(dasar_kode.symmetric_difference(himpunan_kode[b])):
                temuan.append({"bahasa": b, "jenis": "fakta_tidak_sejajar",
                               "pesan": f"Kode {k} hanya ada di sebagian bahasa."})
            for t in sorted(dasar_token.symmetric_difference(himpunan_token[b])):
                temuan.append({"bahasa": b, "jenis": "angka_tidak_sejajar",
                               "pesan": f"Token '{t}' tidak sama di semua bahasa."})

    return {
        "ok": True,
        "sku": sku,
        "konsisten": not temuan,
        "jumlah_temuan": len(temuan),
        "temuan": temuan,
        "per_bahasa": per_bahasa,
        "verdict": "KONSISTEN" if not temuan else "TIDAK_KONSISTEN",
        "catatan": "Ini pemeriksaan konsistensi fakta terstruktur, bukan penilaian kualitas terjemahan.",
    }
