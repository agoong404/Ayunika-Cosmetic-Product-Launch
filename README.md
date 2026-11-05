# Lolos — Reviewer Konten Peluncuran Kosmetik

> **Challenge C — The Creator Agent** · skenario *product launch* (bodycare & beautycare)
> Tencent Cloud Hackathon Indonesia 2026

**Lolos** adalah sistem tiga agent yang membantu tim marketing UMKM kosmetik menulis
konten peluncuran yang **lolos aturan sebelum terbit**: Planner menyusun kerangka,
Writer menulis, Reviewer menolak dengan **nomor aturan + kutipan + perbaikan konkret** —
dan seluruh siklus tercatat di audit log hash-chain yang tidak bisa diubah diam-diam.

Blurb: *Reviewer konten peluncuran kosmetik: tolak, perbaiki, setujui.*

---

## Jalankan cepat

```bash
# 1. siklus penuh lewat jembatan WorkBuddy (tanpa API key — model dijawab manual)
python -m agents.workbuddy reset
python -m agents.workbuddy start AY-SR-101 tiktok   # sesi + prompt Planner
python -m agents.workbuddy save plan  agents/.wb/jawaban-plan.json
python -m agents.workbuddy next                     # prompt Writer
python -m agents.workbuddy save draft agents/.wb/draf-agensi-1.md   # → lapis-1 menilai
python -m agents.workbuddy next                     # prompt lapis-2 (model)
python -m agents.workbuddy save findings agents/.wb/temuan-lapis2-1.json  # verdict final

# 2. tiga suite uji (satu perintah per baris — aman di PowerShell & Git Bash)
cd engine
python run_reviewer_tests.py          # 73/73 asersi mekanisme
python run_official_cases.py --ulang 50   # 16 utama + 6 cadangan × 50 = 1100 eksekusi
python governance.py verify           # UTUH — rantai hash terverifikasi
cd ..
python -m agents.harness              # 40/40 run loop (termasuk kegagalan agent)
# catatan: C-17 (kartu produk + OCR) butuh binary Tesseract — lihat docs/MULAI_DARI_SINI.md
```

## Struktur

| Jalur | Isi |
|---|---|
| `engine/reviewer.py` | Reviewer dua lapis: kode (R-03/R-06/R-07/…) + model (R-04/R-05/R-07/R-10/R-12) dengan penjaga kutipan |
| `engine/layer2.py` + `engine/prompts/` | Lapis model: wewenang dibatasi, setiap temuan wajib mengutip teks yang ADA di draf |
| `engine/pipeline.py` | Orkestrator 3 agent, maks 3 iterasi, lalu eskalasi |
| `engine/governance.py` | Audit log append-only hash-chain + gerbang approval (token sekali pakai) |
| `engine/run_official_cases.py` | Harness 26 kasus Challenge C (16 utama + 6 cadangan dieksekusi, 4 N/A) |
| `agents/` | Planner, Writer (deterministik + mode model), jembatan WorkBuddy, LLM adapter |
| `skills/` | Tiga skill WorkBuddy (`lolos-planner`, `lolos-writer`, `lolos-reviewer`) + `sync.py` |
| `dataset_c/` | Dataset Challenge C: brief, lembar produk, rulebook R-01..R-21, riwayat konten disetujui |
| `submission_templates/` | Dokumen submission 00–07 + 25 kartu bukti `shots/` + cover |
| `docs/` | Rekonsiliasi kasus resmi, laporan hasil, catatan percobaan |

## Status jujur

- **Terverifikasi:** 1100 eksekusi kasus resmi, hasil konsisten; 73/73 asersi mekanisme;
  40/40 run loop; rantai audit UTUH.
- **Belum diuji:** lapis model dengan provider sungguhan — yang terbukti baru *jalurnya*
  (12 asersi dengan klien palsu + siklus jembatan), bukan kualitas keluaran model nyata.
- **N/A:** C-15 (multibahasa), C-17 (aset gambar), C-18 (suntingan manusia), C-19, C-20 —
  butuh kapabilitas di luar skenario yang dipilih. Tidak dilebarkan jadi "lulus".
- Detail lengkap: `submission_templates/01_accountability_sheet.md` dan
  `submission_templates/02_test_results.md` (termasuk 3 kegagalan yang pernah terjadi).
