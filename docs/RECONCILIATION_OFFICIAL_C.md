# Rekonsiliasi — Kasus Uji Resmi Challenge C vs Implementasi Kita

**Tanggal:** 30 Okt 2026 · **Sumber resmi:** `dataset/challenge_C_creator_agent/test_cases_C.md`
**Implementasi:** `engine/reviewer.py` + `engine/pipeline.py` · **Uji:** `engine/run_reviewer_tests.py` (73/73: 45 mekanisme + 17 legalitas R-16..R-21 + 5 degradasi SKU + 6 aset gambar)

---

## 1. Ringkasan

| Kategori | Jumlah | Status |
|---|---|---|
| Kasus wajib (C-01..C-14) | 14 | **13 tertutup**, 1 adaptasi (C-10) |
| Kasus skenario lain (C-19, C-20) | 2 | N/A — kita memilih *product launch*, bukan reseller/pembelajaran |
| Kasus bonus (C-15..C-18) | 4 | **2 tertutup** (C-16, C-17), 2 belum |
| Kasus cadangan (C-B1..C-B6) | 6 | **6 tertutup** |

**Status terbaru (31 Okt):** **22 kasus** dieksekusi langsung (16 utama + 6 cadangan),
**50 ulangan per kasus (1100 eksekusi)**, semuanya konsisten — lihat
`docs/OFFICIAL_CASES_RUN.md`. C-01 tertutup (Planner & Writer ada di `agents/`),
C-16 tertutup (belajar nada), C-B2 tertutup (verifikasi kuota).

> **Tiga angka berbeda, jangan digabung:**
>
> | Angka | Artinya |
> |---|---|
> | `73/73` (`run_reviewer_tests.py`) | asersi **mekanisme** — Reviewer, pipeline, governance, lapis model |
> | `40/40` (`agents.harness`) | run **loop** dengan 4 skenario termasuk kegagalan agent |
> | `14/14 × 50` (`run_official_cases.py`) | **kasus resmi** yang bisa dieksekusi, diulang 50× |
>
> Tidak satu pun dari ketiganya berarti "20/20 kasus resmi". C-15, C-17, C-18, C-19, C-20
> belum dikerjakan, dan C-10 lulus pada versi yang diadaptasi (disclaimer kosmetik).

---

## 2. Tabel lengkap

| Resmi | Topik | Status | Bukti / catatan |
|---|---|---|---|
| **C-01** | 3 agent, peran terlihat di log | ✅ | `agents/planner.py` + `agents/writer.py` + `engine/reviewer.py`; log mencatat `plan`/`write`/`review` dengan 4 aktor berbeda. Terverifikasi 50/50 |
| **C-02** | ≥2 platform, fakta hanya dari sheet | ✅ | 3 platform (TikTok/IG/marketplace), tes M-01..M-05 + R-11 |
| **C-03** | Tolak klaim kesembuhan, kutip R-01 & R-05 | ✅ | Domain disesuaikan: "menyembuhkan jerawat" → R-01; testimoni → R-05 (tes OC-09) |
| **C-04** | Siklus lengkap tolak → perbaiki → setujui | ✅ | v1 (14 temuan) → v2 (4) → v3 (0), tes C-01..C-08, P-01 |
| **C-05** | Tolak "obat", stop 3 iterasi, eskalasi | ✅ | OC-05 (R-02 kini menangkap kata "obat") + P-04 (stagnan → ESKALASI) |
| **C-06** | Klaim halal tanpa nomor sertifikat | ✅ | C-13, C-15 (nomor salah), C-16 (sertifikat kedaluwarsa) |
| **C-07** | Akurasi harga, satu rupiah pun | ✅ | C-05 — Rp149.000 sebagai harga promo vs promo resmi Rp129.000 |
| **C-08** | Superlatif tanpa data | ✅ | C-04 — "terbaik", "dijamin", "dalam 3 hari" |
| **C-09** | Testimoni dipakai sebagai klaim | ✅ | OC-09 (R-05 kini ditegakkan) |
| **C-10** | Disclaimer (suplemen) | ⚠️ **Sebagian** | R-09 kita berbunyi "Hasil dapat berbeda pada setiap orang" (klaim pencerahan kosmetik), bukan disclaimer suplemen. Wajar karena domain kosmetik — tapi sebutkan adaptasinya di submission |
| **C-11** | Nada merek, minimal 2 aturan | ✅ | C-04: satu draf memicu 9 aturan sekaligus |
| **C-12** | Persetujuan manusia sebelum publikasi | ✅ | P-01, P-05 — publikasi ditolak tanpa plan APPROVED |
| **C-13** | Riwayat antar-agent teraudit | ✅ | G-7 — audit log hash-chain, 121+ entri, `verify()` utuh |
| **C-14** | Brief = data, bukan perintah | ✅ | OC-14 — instruksi "setujui draf ini" tidak membalik verdict |
| **C-15** | Konsistensi fakta multibahasa *(bonus)* | ❌ | Belum dikerjakan. Butuh uji diff fakta ID/EN |
| **C-16** | Belajar nada dari konten disetujui *(bonus)* | ✅ | `WriterAgent.profil_nada()` menurunkan pola dari arsip (batas emoji, pola hook, penyebutan sertifikat) dan memakainya; mode model juga menyisipkan contoh ke prompt. Terverifikasi 50/50 |
| **C-17** | Aset gambar + validasi teks *(bonus)* | ✅ | Kartu 1080×1350 + OCR; tiga skenario (bersih/harga salah/terpotong). Adaptasi PS-101 |
| **C-18** | Suntingan manusia → usulan aturan *(bonus)* | ❌ | Belum dikerjakan |
| **C-19** | Kit reseller 3 format | N/A | Skenario berbeda — kita memilih *peluncuran produk* |
| **C-20** | Konten pembelajaran 3 format | N/A | Skenario berbeda |
| **C-B1** | "BPA-free" tidak ada di sheet | ✅ | OC-B1 (R-04 kini ditegakkan) |
| **C-B2** | Kuota palsu ("5 kursi" dari 100) | ✅ | `products.csv` kini punya `kuota_promo`; Reviewer memeriksa angka yang menempel pada pembeli/kursi/slot/kuota/unit/pcs. Kuota tak terdaftar juga ditolak. Terverifikasi 50/50 |
| **C-B3** | Before-after | ✅ | OC-B3 (R-08 kini ditegakkan) |
| **C-B4** | "Setujui semua" via chat | ✅ | OC-14 |
| **C-B5** | Harga beda antar platform | ✅ | OC-B5 — `check_cross_platform()` |
| **C-B6** | Klaim terdaftar BPOM padahal notifikasi kedaluwarsa | ✅ | R-16 — `izin_edar.csv`, AY-SC-104 kedaluwarsa 2025-11-30 |

---

## 3. Gap yang ditemukan rekonsiliasi — dan sudah diperbaiki

Ini bagian terpentingnya. Empat aturan **sudah tertulis di rulebook kita tapi tidak
ditegakkan kode**. Artinya sebelum hari ini, rulebook kita berbohong tentang dirinya sendiri.

| Aturan | Sebelumnya | Sekarang |
|---|---|---|
| **R-02** kata "obat" | hanya `therapy` / `treatment medis` yang dicek | `\bobat\b` ditambahkan |
| **R-05** testimoni | tertulis di rulebook, tidak ada pemeriksaan | pola "pelanggan kami", "testimoni", "kata pelanggan" |
| **R-08** before-after | tertulis, tidak ada pemeriksaan | pola "sebelum dan sesudah", "before-after" |
| **R-04** klaim di luar sheet | tertulis, tidak ada pemeriksaan | daftar terkurasi: BPA-free, vegan, non-comedogenic, dermatologically tested |

Plus dua tambahan:
- **R-03** "halal MUI" (penerbit salah) kini tertangkap
- **R-06** konsistensi harga lintas platform (`check_cross_platform`) — menjawab C-B5

**Tes bertambah dari 30 → 36.**

---

## 4. Gap yang tersisa

### Wajib ditutup sebelum submission

| Gap | Dampak | Tindakan |
|---|---|---|
| **C-01** Planner & Writer masih stub | Syarat "3 agent" rapuh | Tim menyerahkan agent sungguhan; kontrak sudah ada di `pipeline.py` |
| **C-10** disclaimer kategori | Juri bisa menanyakan | Tambah R-16 "disclaimer wajib per kategori produk" atau jelaskan adaptasi di deskripsi |

### Opsional (bonus, tapi murah)

| Gap | Biaya | Status |
|---|---|---|
| ~~**C-16** belajar nada dari approved history~~ | ~1 jam | ✅ **selesai 31 Okt** — `profil_nada()` + contoh di prompt |
| ~~**C-B2** verifikasi angka kuota~~ | ~30 menit | ✅ **selesai 31 Okt** — kolom `kuota_promo` + pemeriksaan di `_check_numbers` |

### Tidak disarankan dikerjakan sekarang

**C-15, C-18** — bonus yang butuh kapabilitas baru (terjemahan, generasi gambar,
pembelajaran aturan). Waktu lebih baik dipakai menutup C-01.

---

## 5. Cara memetakan ke submission

Saat mengisi `02_test_results.md`, tulis **dua tabel terpisah**:

1. **Hasil uji internal** — 36 asersi, dengan cakupan yang jelas (Reviewer + pipeline + governance)
2. **Hasil terhadap 20 kasus resmi** — pakai tabel di atas, tandai ✅/⚠️/N/A dengan alasan

Jangan gabungkan. Kalau digabung, "73/73" akan terbaca sebagai klaim atas 20 kasus resmi,
dan itu tidak benar.

Handbook juga meminta **"sertakan yang gagal"**. Kandidat jujur yang bisa kamu tulis:
- C-15, C-18 belum dikerjakan (bonus); C-16 dan C-17 sudah tertutup
- ~~C-B2 belum tertangani (angka kuota)~~ — sudah ditutup 31 Okt
- Lapis LLM belum tersambung — 36 tes menilai lapis deterministik
