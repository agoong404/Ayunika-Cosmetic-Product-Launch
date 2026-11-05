# Coba Sendiri — Reviewer Agent Challenge C

Panduan 5 percobaan manual. Tidak perlu API key, tidak perlu install apa pun,
tidak perlu internet (kecuali percobaan 4).

---

## 0. Persiapan (30 detik)

Python sudah ada di mesinmu. Cek:

```bash
python --version
```

Kalau keluar `Python 3.13.x`, siap. **Tidak ada dependency** — semua pakai
standard library.

Lalu masuk ke folder kerja. **Semua perintah di bawah dijalankan dari `engine/`:**

```bash
cd "C:/.Hackathon Project/engine"
```

> Catatan: `cd` wajib, karena kode membaca `../dataset_c` secara relatif.

---

## 1. Lihat satu siklus penuh (1 perintah)

```bash
python pipeline.py
```

Yang akan kamu lihat: Planner → Writer → Reviewer berputar tiga kali, lalu
gerbang approval, lalu terbit.

**Yang perlu diperhatikan:**

- `iterasi 1: TOLAK · 14 temuan` → `iterasi 2: TOLAK · 4` → `iterasi 3: LOLOS`
- ada `plan: PLAN-XXXXXXXX` di akhir — itu token approval-nya
- konten final yang dicetak adalah draf v3

**Kalau ingin melihat versi gagal:** buka `pipeline.py`, cari `ScriptedWriter([...])`,
ubah isinya jadi tiga path draf v1 semua. Jalankan lagi — hasilnya harus
**ESKALASI**, bukan TERBIT. Itu membuktikan batas 3 iterasi benar-benar menghentikan.

---

## 2. Uji draf buatanmu sendiri (inti dari semuanya)

### 2a. Siapkan file

Buat file baru, mis. `C:/.Hackathon Project/dataset_c/sample_drafts/DRAFT-SAYA.md`.
Isinya bebas — tulis apa saja seperti caption yang mau kamu terbitkan.

Contoh untuk disalin:

```
Serum terbaik nomor 1 di Indonesia! Dijamin memutihkan dalam 3 hari.
Sudah halal, aman untuk semua jenis kulit tanpa efek samping.
Promo Rp149.000 untuk 100 pembeli pertama.
```

### 2b. Jalankan

```bash
python reviewer.py ../dataset_c/sample_drafts/DRAFT-SAYA.md AY-SR-101 tiktok 1
```

Format perintahnya:

```
python reviewer.py <file_draf> <SKU> <platform> <iterasi>
```

- `<SKU>` — salah satu dari `AY-SR-101`, `AY-BL-102`, `AY-FW-103`, `AY-SC-104`
- `<platform>` — `tiktok`, `instagram`, atau `marketplace`
- `<iterasi>` — angka 1–3 (mempengaruhi keputusan akhir: di iterasi 3, gagal = ESKALASI)

### 2c. Baca hasilnya

Tiap temuan punya tiga baris:

```
✗ R-07 [deterministik] “Dijamin memutihkan dalam 3 hari.”
    alasan: janji hasil: “dijamin” melanggar R-07 — Superlatif & janji hasil dilarang.
    perbaiki: Hapus janji hasil. Ganti dengan klaim yang ada di lembar produk.
```

- **kutipan** — kalimat dari drafmu yang bermasalah (harus ada persis di drafmu)
- **alasan** — aturan mana yang dilanggar dan mengapa
- **perbaiki** — saran konkret

### 2d. Perbaiki dan ulangi

Hapus semua yang ditandai, jalankan lagi dengan `iterasi 2`. Ulangi sampai
`✔ tidak ada pelanggaran`. Itu siklus tolak → perbaiki → setujui, versimu sendiri.

---

## 3. Percobaan paling meyakinkan: satu teks, empat jawaban berbeda

Ini yang paling layak kamu tunjukkan ke orang lain. **Teks yang sama persis**,
tapi hasilnya beda karena status sertifikat produknya beda.

Buat satu file `DRAFT-SAYA.md`:

```
Produk ini sudah bersertifikat halal dan aman dipakai setiap hari.
Teksturnya ringan, cepat meresap, cocok untuk kulit kusam.
```

Lalu jalankan empat kali, ganti SKU-nya:

```bash
python reviewer.py ../dataset_c/sample_drafts/DRAFT-SAYA.md AY-SR-101 tiktok 1
python reviewer.py ../dataset_c/sample_drafts/DRAFT-SAYA.md AY-BL-102 tiktok 1
python reviewer.py ../dataset_c/sample_drafts/DRAFT-SAYA.md AY-FW-103 tiktok 1
python reviewer.py ../dataset_c/sample_drafts/DRAFT-SAYA.md AY-SC-104 tiktok 1
```

Keempatnya **TOLAK**, tapi alasannya berbeda semua:

| SKU | Status sertifikat | Alasan penolakan |
|---|---|---|
| AY-SR-101 | belum ada | klaim halal, sertifikat belum terbit |
| AY-BL-102 | aktif s/d 2029 | **nomornya belum dicantumkan** — bukan karena tidak halal |
| AY-FW-103 | masih pengajuan | klaim halal padahal baru diajukan |
| AY-SC-104 | kedaluwarsa 31 Agu 2026 | nomor ada, tapi tidak berlaku |

**Kenapa ini penting:** kalau kamu hanya punya dua status (halal / tidak), keempat
baris ini akan tampak sama. Sistem yang membedakan alasannya bisa memberi tahu
**apa yang harus diperbaiki** — dan itu bedanya alat kepatuhan dengan penolak otomatis.

### Lanjutkan satu baris sampai lolos

Untuk AY-BL-102, tambahkan nomor sertifikatnya:

```
Produk ini bersertifikat halal, nomor ID32110084875141025.
Teksturnya ringan, cepat meresap, dirancang untuk kulit kusam.
```

```bash
python reviewer.py ../dataset_c/sample_drafts/DRAFT-SAYA.md AY-BL-102 tiktok 2
```

Hasilnya `LOLOS`. Perhatikan: satu-satunya yang berubah adalah **bukti**, bukan
kalimatnya.

---

## 4. Verifikasi nomor sertifikat ke registri BPJPH

Butuh internet. Dua percobaan: nomor nyata vs nomor mock.

```bash
# nyata — ada di registri publik BPJPH
python reviewer.py verify ID32110019969360724

# mock — dipakai produk fiktif Ayunika
python reviewer.py verify SERT-AY-102
```

Yang pertama mengembalikan `ditemukan: true` beserta daftar produk yang tercakup.
Yang kedua `ditemukan: false`.

**Yang perlu kamu renungkan saat melihat hasilnya:** nomor nyata itu mencakup
**ratusan produk dari puluhan merek**. Itu model maklon — satu sertifikat dipakai
banyak merek. Artinya "produk saya ada di bawah sertifikat itu" bukan bukti;
yang harus dicek adalah apakah SKU-nya benar-benar terdaftar.

---

## 5. Lihat catatan audit dan uji apakah bisa diubah

```bash
python governance.py tail 10
python governance.py verify
```

`tail` menampilkan 10 kejadian terakhir: siapa, aksi apa, hasilnya apa.
`verify` memeriksa rantai hash — hasilnya `UTUH: ...`.

> Log ini sudah berisi ~460 entri dari sesi pengembangan. Kalau kamu ingin mulai
> dari kosong supaya jejakmu sendiri lebih mudah dibaca, **pindahkan** foldernya,
> jangan hapus:
>
> ```bash
> mv .audit .audit.lama
> ```
>
> Prinsipnya append-only — menghapus log adalah hal yang justru ingin dicegah
> sistem ini.

Sekarang coba rusak dengan sengaja. Buka `engine/.audit/audit.jsonl`, ubah satu
kata di salah satu baris (mis. ganti `TOLAK` jadi `LOLOS`), simpan, lalu:

```bash
python governance.py verify
```

Hasilnya `RUSAK: entri #N isinya diubah`. Kembalikan file-nya, dan `verify`
kembali `UTUH`.

Itu yang membedakan "log" dengan "file teks": perubahan sekecil apa pun terdeteksi.

---

## 6. Menjalankan seluruh uji otomatis

```bash
python run_reviewer_tests.py
```

Harus keluar `73/73 lulus` di akhir.

> **Baca ini sebelum mengutip angkanya:** 45 itu asersi internal untuk mekanisme
> Reviewer (termasuk lapis model), pipeline, dan governance. Ini **bukan** 20 kasus
> resmi Challenge C.
> Jangan gabungkan keduanya saat mengisi laporan submission.

---

## Yang tidak akan kamu lihat (dan itu wajar)

| Hal | Kenapa |
|---|---|
| Penilaian nada & parafrase | Lapis LLM belum tersambung. Yang jalan baru lapis deterministik (kode) |
| Reviewer "memperbaiki" draf | Memang tidak boleh — Reviewer hanya menilai. Perbaikan tugas Writer |
| Nama Planner/Writer sungguhan | Masih `TemplatePlanner` & `ScriptedWriter` (pengganti sementara) |
| Sertifikat Ayunika ditemukan di BPJPH | Nomornya mock, sengaja. Produknya fiktif |

---

## Kalau kamu menemukan pelanggaran yang lolos

Itu **temuan berharga**, bukan kegagalan. Catat:

1. Teks draf yang lolos padahal melanggar
2. Aturan mana di `dataset_c/rulebook_claims.md` yang seharusnya menangkapnya
3. Apakah aturan itu sudah ada di `PROHIBITED` (`engine/reviewer.py`, baris ~55)

Kalau aturannya ada di rulebook tapi tidak ada di `PROHIBITED`, itu bug — persis
jenis bug yang ditemukan saat rekonsiliasi (R-02, R-04, R-05, R-08 dulu tertulis
tapi tidak ditegakkan). Tambahkan polanya, lalu jalankan ulang tes untuk
memastikan tidak ada regresi.

Kalau aturannya belum ada sama sekali, itu keputusan produk: tambahkan ke
rulebook **dan** ke kode, jangan hanya salah satu.
