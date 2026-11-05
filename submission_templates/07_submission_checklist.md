# Checklist Submission — Lolos · Tencent Cloud Hackathon Indonesia 2026

> **DEADLINE: 1 November 2026** · Form: https://forms.gle/y1aHBH4BsrytXDxdA
> Status per **31 Oktober 2026, 20:30 WIB**. Yang belum, ditandai jujur — bukan dicentang.

## Jadwal (aktual, bukan rencana)

| Tanggal | Target | Status |
|---|---|---|
| 27 Okt | Pilih challenge · dataset siap · akun WorkBuddy | ✅ (waktu itu masih ke arah A) |
| 28 Okt | Bangun agent inti + gate approval + audit log | ✅ `engine/governance.py` |
| 29 Okt | Uji 20 kasus · screenshot | ✅ sebagian — 45/45 asersi mekanisme |
| 30 Okt | Pindah ke Challenge C · dataset beautycare · Reviewer 2 lapis | ✅ keputusan diambil, bukan ditunda |
| 31 Okt | 1100 eksekusi · 27 gambar · dokumen 00–07 · video | ✅ |
| 1 Nov | **Submit PAGI** | ⬜ |

## Item Submission (handbook Bag. 7)

| # | Item | Status | Wajib | Berkas |
|---|---|---|---|---|
| 1 | Project title | ✅ **Lolos** | WAJIB | — |
| 2 | Short blurb (<10 kata) | ✅ 7 kata: "Reviewer konten peluncuran kosmetik: tolak, perbaiki, setujui." | WAJIB | `03` |
| 3 | Project description (4 bagian) | ✅ | WAJIB | `03_project_description.md` |
| 4 | Accountability sheet | ✅ 5 aturan + mekanisme + keterbatasan | WAJIB | `01_accountability_sheet.md` |
| 5 | Test results + screenshot (incl. FAIL) | ✅ 22 PASS/26, 3 kegagalan tercatat, 27 gambar | WAJIB | `02_test_results.md` + `shots/` |
| 6 | Architecture diagram | ✅ PNG 2960×2600 + SVG + Mermaid — **diregenerasi 31 Okt** agar mencerminkan Reviewer dua lapis + kuota | WAJIB | `diagram/architecture_challenge_c.png` |
| 7 | Demo video 5–8 menit | ✅ **7:02** — 30 scene dari keluaran nyata, caption terbakar. **Tanpa narasi suara**; bisa ditambahi voice-over | WAJIB | `video/Lolos_Demo.mp4` |
| 8 | Product sharing (WorkBuddy) | ✅ | WAJIB | `06_product_sharing.md` |
| 9 | Source code / export + bukti | ⚠️ `README.md` root siap 31 Okt (jalankan cepat + struktur + status jujur); **repo publik belum dibuat** — ikuti catatan `.gitignore` di bawah | WAJIB | `README.md` |
| 10 | Cover image 16:9 (380×216) | ✅ **cover.png 1520×864 @2x** (rasio sama), dibuat dari `diagram/build_cover.py` | OPSIONAL | `submission_templates/cover.png` |
| 11 | Project link (demo live) | ⬜ bonus; jalur API belum disambung ke provider | BONUS | — |

## Yang Harus Dikerjakan Malam Ini / Besok Pagi

1. ~~**Rekam video**~~ ✅ sudah ada `video/Lolos_Demo.mp4` (7:02, 30 scene, caption terbakar).
   Kalau mau menambah narasi suara, rekam voice-over di atas potongan ini — timecode-nya sudah pas.
2. **Buat repo publik.** `.gitignore` sudah siap di root dan sudah memblokir:
   - `dataset_halal/shared/contacts.csv` dan `dataset/shared/contacts.csv` memuat
     **NIK + nomor telepon** (mock, tapi formatnya nyata) → **jangan dipublikasikan**
   - `engine/.audit/`, `engine/.cache_bpjph/`, `agents/.wb/` → state runtime
   - `Tencent_Cloud_Hackathon_Indonesia_2026_Handbook.pdf` → materi panitia
   - `research/src/*.pdf` → dokumen regulasi pihak ketiga
   - `dataset/` (dataset panitia) utuh → cek apakah lisensinya melarang redeploy
3. ~~Cover image~~ ✅ selesai 31 Okt — `submission_templates/cover.png`.
4. **Submit pagi**, simpan tangkapan konfirmasi.

## Kriteria Kualitas (rubrik 10×10) — penilaian sendiri

| Kriteria | Kondisi | Catatan |
|---|---|---|
| Impact & Relevance | ✅ | Masalah nyata; 4 dari 5 pesan brief melanggar |
| Human-Centered Design | ✅ | Approval manusia, bukan otomatis terbit |
| AI Interaction | ✅ | 3 agent + loop + eskalasi; bukan satu prompt |
| Technical Execution | ✅ | 1100 eksekusi, hasil jujur termasuk 3 kegagalan |
| Feasibility | ⚠️ | Jalur produksi ada (API adapter), belum diuji provider nyata |
| Demo & Storytelling | ⬜ | Video belum ada — ini risiko terbesar |
| Innovation | ✅ | Reviewer dua lapis + penjaga kutipan + kuota vs registri |
| UX & Accessibility | ⚠️ | Masih CLI; UI belum dibangun |
| Responsible AI & Ethics | ✅ | 5 aturan terbukti; 0 kegagalan kritis; keterbatasan terbuka |
| Overall | ⚠️ | Bergantung pada video |

## Red Flags — Status

1. Blurb ≥10 kata → **aman (7)**
2. Test results tanpa screenshot / tanpa FAIL → **aman** (27 gambar, 3 FAIL tercatat)
3. Accountability sheet generik → **aman** (mekanisme + kode, bukan janji)
4. Video tanpa adegan tolak/approval → **risiko** jika video tidak jadi
5. Kegagalan disembunyikan → **aman**
6. Submit mepet tenggat → **risiko**; targetkan 1 Nov pagi

## Setelah Submit

- [ ] Simpan tangkapan konfirmasi form
- [ ] Pantau pengumuman finalis (10 Nov)
- [ ] Demo Day 27 Nov: latih uji kejutan 90 detik dengan **kasus baru** — kandidat terbaik:
      "boleh nggak kami bilang 'BPOM certified'?" (klaim otoritas, belum ada aturannya)
