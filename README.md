# Ayunika Care — Reviewer Konten Peluncuran Kosmetik

> **Challenge C — The Creator Agent** · skenario *product launch* (bodycare & beautycare)
> Tencent Cloud Hackathon Indonesia 2026

**Ayunika Care** adalah sistem tiga agent yang membantu tim marketing UMKM kosmetik menulis
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
./.venv/Scripts/python.exe -m mcp_server.run_tests   # 88/88 pemeriksaan MCP
# catatan: C-17 (kartu produk + OCR) butuh binary Tesseract — lihat docs/MULAI_DARI_SINI.md
```

**Jalur MCP & situs publik** (lihat `mcp_server/README.md`, `web/README.md`, `deploy/RAILWAY.md`):

```bash
# MCP lokal lewat stdio — daftar 19 tool, dipakai WorkBuddy lewat ~/.workbuddy-ai/mcp.json
./.venv/Scripts/python.exe -m mcp_server.smoke_client

# Situs publik (BFF tanpa dependensi; butuh MCP_URL + MCP_TOKEN)
cd web
node server/index.js          # http://localhost:8080
```

Situs hanya menjangkau 5 tool (`list_products`, `get_rulebook`, `run_cycle`,
`request_approval`, `audit_tail`). `approve_publication` **tidak ditulis** di BFF —
persetujuan tetap memakai kunci yang hanya dipegang manusia.

## Struktur

| Jalur | Isi |
|---|---|
| `engine/reviewer.py` | Reviewer dua lapis: kode (R-03/R-06/R-07/…) + model (R-04/R-05/R-07/R-10/R-12) dengan penjaga kutipan |
| `engine/layer2.py` + `engine/prompts/` | Lapis model: wewenang dibatasi, setiap temuan wajib mengutip teks yang ADA di draf |
| `engine/pipeline.py` | Orkestrator 3 agent, maks 3 iterasi, lalu eskalasi |
| `engine/governance.py` | Audit log append-only hash-chain + gerbang approval (token sekali pakai) |
| `engine/run_official_cases.py` | Harness 26 kasus Challenge C (16 utama + 6 cadangan dieksekusi, 4 N/A) |
| `agents/` | Planner, Writer (deterministik + mode model), jembatan WorkBuddy, LLM adapter |
| `skills/` | Tiga skill WorkBuddy (`ayunika-planner`, `ayunika-writer`, `ayunika-reviewer`) + `sync.py` |
| `expert/` | Expert WorkBuddy **Ayunika Compliance Team** (4 agent) + `build.py` yang menghasilkan avatar tim |
| `mcp_server/` | Server MCP, 19 tool stateless di atas `engine/` + `agents/`; transport stdio & HTTPS |
| `web/` | Situs publik: BFF Node tanpa dependensi + frontend; `approve_publication` sengaja tidak ada |
| `deploy/` | Dockerfile, entrypoint, nginx, systemd, dan runbook Railway |
| `dataset_c/` | Dataset Challenge C: brief, lembar produk, rulebook R-01..R-21, riwayat konten disetujui |
| `submission_templates/` | Dokumen submission 00–07 + 26 kartu bukti `shots/` + 1 kartu produk `cards/` + cover |
| `docs/` | Rekonsiliasi kasus resmi, laporan hasil, catatan percobaan |
| `log.md` | Catatan 24 putaran build, termasuk keputusan desain dan koreksi |

## Status jujur

- **Terverifikasi:** 1100 eksekusi kasus resmi, hasil konsisten; 73/73 asersi mekanisme;
  88/88 uji MCP server; 40/40 run loop; rantai audit UTUH.
- **Live:** MCP service di `mcp-service-ayunika-production.up.railway.app` — `/health` aktif,
  `/mcp` menolak permintaan tanpa token (fail-closed). Konfigurasi klien: `mcp_server/mcp.example.json`.
- **Belum diuji:** lapis model dengan provider sungguhan — yang terbukti baru *jalurnya*
  (12 asersi dengan klien palsu + siklus jembatan), bukan kualitas keluaran model nyata.
- **Sudah dideploy:** kode rebrand (commit `3e89e56`) sudah di-push ke `main`; situs `web/` jalan di demo `:8080` dan otomatis ter-deploy ulang dari repo bila Railway terhubung. Engine MCP tetap live dengan namespace `lolos` (tidak berubah).
- **Cakupan: prototipe untuk dataset Challenge C, bukan produksi.** Mesin membaca
  `dataset_c/` (kontrak data: `products.csv`, `certificates.csv`, `rulebook_claims.md`,
  lembar produk). Nomor sertifikat Ayunika **MOCK**; penomoran R-xx adalah nomor
  internal, bukan pasal hukum; `bpjph_client.py` memakai halaman publik BPJPH yang
  tidak resmi dan tidak boleh jadi backend produksi tanpa izin. SKU di luar registri
  sengaja menghasilkan `PERLU_DATA` — bukan lulus. Untuk pemakaian nyata: ganti isi
  folder data dengan registri terverifikasi, petakan R-xx ke dasar hukum yang sah,
  uji lapis model dengan provider sungguhan, dan minta tinjauan regulatory. Kami
  tidak mengklaim akurasi di luar 26 kasus resmi.
- **N/A:** 4 kasus — C-15 (multibahasa), C-18 (suntingan manusia), C-19, C-20 — butuh
  kapabilitas di luar skenario yang dipilih. Tidak dilebarkan jadi "lulus".
  (C-17 aset gambar **sudah PASS** lewat validasi OCR.)
- Detail lengkap: `submission_templates/01_accountability_sheet.md` dan
  `submission_templates/02_test_results.md` (termasuk 3 kegagalan yang pernah terjadi).
