# Checklist Submission — Ayunika Care · Tencent Cloud Hackathon Indonesia 2026

> **DEADLINE: 7 November 2026** (diundur dari 1 November) · Form: https://forms.gle/y1aHBH4BsrytXDxdA
> Status per **6 November 2026, 19:45 WIB**. Yang belum, ditandai jujur — bukan dicentang.

## Jadwal (aktual, bukan rencana)

| Tanggal | Target | Status |
|---|---|---|
| 27 Okt | Pilih challenge · dataset siap · akun WorkBuddy | ✅ (waktu itu masih ke arah A) |
| 28 Okt | Bangun agent inti + gate approval + audit log | ✅ `engine/governance.py` |
| 29 Okt | Uji 20 kasus · screenshot | ✅ sebagian — 45/45 asersi mekanisme |
| 30 Okt | Pindah ke Challenge C · dataset beautycare · Reviewer 2 lapis | ✅ keputusan diambil, bukan ditunda |
| 31 Okt | 1100 eksekusi · 27 gambar · dokumen 00–07 · video | ✅ |
| 2–5 Nov | MCP server (19 tool) + situs publik + deploy Railway; repo publik | ✅ |
| 6 Nov | Sinkronisasi dokumen; 3 kapabilitas bonus (C-15/17/18) + expert tim "Ayunika Compliance Team" (4 agent) | ✅ |
| 7 Nov | **Submit PAGI** | ⬜ |

## Item Submission (handbook Bag. 7)

| # | Item | Status | Wajib | Berkas |
|---|---|---|---|---|
| 1 | Project title | ✅ **Ayunika Care** | WAJIB | — |
| 2 | Short blurb (<10 kata) | ✅ 7 kata: "Reviewer konten peluncuran kosmetik: tolak, perbaiki, setujui." | WAJIB | `03` |
| 3 | Project description (4 bagian) | ✅ | WAJIB | `03_project_description.md` |
| 4 | Accountability sheet | ✅ 5 aturan + mekanisme + keterbatasan | WAJIB | `01_accountability_sheet.md` |
| 5 | Test results + screenshot (incl. FAIL) | ✅ 22 PASS/26, 3 kegagalan tercatat, 27 gambar | WAJIB | `02_test_results.md` + `shots/` |
| 6 | Architecture diagram | ✅ PNG 2960×2600 + SVG + Mermaid — **diregenerasi 31 Okt** agar mencerminkan Reviewer dua lapis + kuota | WAJIB | `diagram/architecture_challenge_c.png` |
| 7 | Demo video 5–8 menit | ✅ **5:07** (`AyunikaCareDemo_v2.mp4`, Remotion, 12 scene, 1080p30, caption Indonesia terbakar, tanpa narasi suara) — cadangan **7:02** (`video/AyunikaCare_Demo.mp4`, 30 scene) | WAJIB | `my-video/out/`, `video/AyunikaCare_Demo.mp4` |
| 8 | Product sharing (WorkBuddy) | ✅ | WAJIB | `06_product_sharing.md` |
| 9 | Source code / export + bukti | ✅ **Repo publik:** `github.com/agoong404/Ayunika-Cosmetic-Product-Launch` (11 commit, working tree bersih). `.gitignore` memblokir NIK, state runtime, dan materi panitia | WAJIB | `README.md` |
| 10 | Cover image 16:9 (380×216) | ✅ **cover.png 1520×864 @2x** (rasio sama), dibuat dari `diagram/build_cover.py` | OPSIONAL | `submission_templates/cover.png` |
| 11 | Project link (demo live) | ✅ **Situs live:** https://ayunika-care.web.id (hero, konsol agent, gerbang review, kartu tim, log audit — 11 state ditangkap untuk video). MCP service: `mcp-service-ayunika-production.up.railway.app/health` → `{"status":"ok","service":"lolos-mcp"}`; `/mcp` tanpa token ditolak (fail-closed) | BONUS | `deploy/RAILWAY.md`, `web/README.md` |

## Yang Tersisa Sebelum Submit

1. **Submit 7 Nov pagi**, simpan tangkapan konfirmasi form.
2. Opsional: rekam voice-over di atas `AyunikaCareDemo_v2.mp4` (5:18) — subtitle Indonesia
   sudah tersedia di `my-video/out/AyunikaCareDemo_id.srt` (56 entri) sebagai basis narasi.
3. Opsional: deploy ulang `web/` bila ada perubahan. `web/.env.example` menunjuk domain MCP
   yang aktif; `MCP_TOKEN` tetap harus diset sebagai Variable, jangan di-commit.

**Sudah selesai** (dibiarkan tercatat, bukan dihapus): video, cover, repo publik,
dan sinkronisasi dokumen. `.gitignore` memblokir `dataset_halal/shared/contacts.csv`
dan `dataset/shared/contacts.csv` (**NIK + nomor telepon**, mock tapi format nyata),
`engine/.audit/`, `engine/.cache_bpjph/`, `agents/.wb/`, handbook panitia,
`research/src/*.pdf`, dan seluruh `dataset/` milik panitia.

## Kriteria Kualitas (rubrik 10×10) — penilaian sendiri

| Kriteria | Kondisi | Catatan |
|---|---|---|
| Impact & Relevance | ✅ | Masalah nyata; 4 dari 5 pesan brief melanggar |
| Human-Centered Design | ✅ | Approval manusia, bukan otomatis terbit |
| AI Interaction | ✅ | 3 agent + loop + eskalasi; bukan satu prompt |
| Technical Execution | ✅ | 1100 eksekusi, hasil jujur termasuk 3 kegagalan |
| Feasibility | ✅ | MCP server live (19 tool, 88/88 uji) + situs publik nol-LLM; **yang belum diuji tetap** lapis model dengan provider sungguhan |
| Demo & Storytelling | ✅ | Video 5:07 (v2, Remotion) — 12 scene, ada adegan klarifikasi, tolak, dan approval; tanpa narasi suara |
| Innovation | ✅ | Reviewer dua lapis + penjaga kutipan + kuota vs registri |
| UX & Accessibility | ✅ | Situs live di https://ayunika-care.web.id; alur utama juga bisa lewat CLI/MCP |
| Responsible AI & Ethics | ✅ | 5 aturan terbukti; gerbang approval di kode; keterbatasan terbuka |
| Overall | ✅ | 9 item WAJIB lengkap; 1 item BONUS sebagian |

## Red Flags — Status

1. Blurb ≥10 kata → **aman (7)**
2. Test results tanpa screenshot / tanpa FAIL → **aman** (27 gambar, 3 FAIL tercatat)
3. Accountability sheet generik → **aman** (mekanisme + kode, bukan janji)
4. Video tanpa adegan tolak/approval → **aman** (Adegan A menolak, Adegan B approval)
5. Kegagalan disembunyikan → **aman**
6. Submit mepet tenggat → **risiko**; targetkan **7 Nov pagi**

## Setelah Submit

- [ ] Simpan tangkapan konfirmasi form
- [ ] Pantau pengumuman finalis (10 Nov)
- [ ] Demo Day 27 Nov: latih uji kejutan 90 detik dengan **kasus baru** — kandidat terbaik:
      "boleh nggak kami bilang 'BPOM certified'?" (klaim otoritas, belum ada aturannya)
