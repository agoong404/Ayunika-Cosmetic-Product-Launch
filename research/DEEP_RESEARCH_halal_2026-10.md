# Deep Research — Ekosistem Halal Indonesia & Implikasinya untuk Case A + D

**Tanggal:** 27 Oktober 2026
**Ruang lingkup:** regulasi, ketersediaan data, dan konsekuensi bisnis — bukan riset pasar konsumen.
**Metode:** penelusuran JDIH BPK + pembacaan teks resmi dua Peraturan BPJPH 2026, ditambah
penelusuran portal SIHALAL dan lanskap aplikasi.
**Batas:** riset ini tidak mengakses database SIHALAL (butuh login) dan tidak mewawancarai pelaku usaha.

---

## Ringkasan untuk pengambil keputusan

1. Regulasi halal Indonesia **bergerak cepat dan spesifik** — ada dua Peraturan BPJPH baru di 2026
   (sanksi dan label tidak halal) yang belum banyak diketahui tim produk.
2. **Sanksi tertinggi untuk pelaku usaha adalah penarikan barang dari peredaran.** Ini argumen
   komersial langsung untuk Case A.
3. **"Tidak halal" adalah kewenangan pelaku usaha sendiri**, dengan kriteria teknis yang rinci —
   bukan kesimpulan pihak ketiga. Ini justifikasi hukum untuk aturan inti dataset.
4. **Ada pencarian sertifikat publik** (`bpjph.halal.go.id/cari/sertifikat`) yang bisa
   diakses mesin, dengan database **sangat luas** (ratusan ribu record, termasuk merek besar
   seperti Indomie 3.252 SKU dan Wardah 1.331 SKU). Presisi butuh kombinasi nama produk +
   nama produsen. Tetap tanpa barcode, komposisi, atau masa berlaku — cukup untuk
   "terdaftar atau tidak", **tidak** cukup untuk "halal atau tidak".
5. Beberapa kriteria teknis di regulasi **memvalidasi jebakan yang sudah ada di dataset** —
   dan satu hal memperbaikinya (cochineal).

---

## Temuan 1 — Kerangka hukum yang berlaku hari ini

| Instrumen | Berlaku | Catatan |
|---|---|---|
| UU 33/2014 (diubah UU 6/2023) | — | Undang-undang pokok JPH |
| PP 42/2024 (LN 2024/229) | — | Pelaksana utama, menggantikan PP 39/2021 |
| PerBPJPH 1/2025 — Satu Data BPJPH | 1 Okt 2025 | Tata kelola data + **hak akses bertingkat** |
| PerBPJPH 5/2025 | 2025 | Kriteria UMKM, jalur pernyataan halal |
| PerBPJPH 7/2025 | 2025 | Komite Fatwa Produk Halal |
| **PerBPJPH 2/2026 — Sanksi Administratif** | **5 Jun 2026** | 19 halaman |
| **PerBPJPH 3/2026 — Keterangan Tidak Halal** | **23 Jul 2026** | 12 halaman |

> Sumber: JDIH BPK, `peraturan.bpk.go.id`. Kedua PDF 2026 sudah diunduh dan dibaca utuh
> (`research/src/`).

**Implikasi:** kalau tim membangun produk halal dan hanya mengutip "UU 33/2014", itu terasa
usang. Menyebut PerBPJPH 3/2026 sebagai dasar aturan "jangan sebut haram sembarangan" akan
langsung menaikkan kredibilitas di depan juri.

---

## Temuan 2 — Sanksi: ujungnya penarikan barang

**PerBPJPH 2/2026, Pasal 7 ayat (1)** — sanksi administratif bagi pelaku usaha:

1. peringatan tertulis
2. denda administratif
3. **pencabutan Sertifikat Halal**
4. **penarikan barang dari peredaran**

**Pasal 3 ayat (2):** Kepala BPJPH berwenang mencabut sertifikat dan menarik barang.
**Pasal 11:** penarikan dijalankan oleh pelaku usaha di bawah pengawasan BPJPH.

**Implikasi untuk Case A (Watchtower):** ini mengubah cerita dari "rapi-rapi dokumen" menjadi
"hindari penarikan produk". Angka yang bisa dipakai di pitch: satu SKU gagal = potensi
penarikan seluruh batch yang beredar, bukan sekadar temuan audit.

---

## Temuan 3 — "Tidak halal" bukan kesimpulan pihak ketiga

**PerBPJPH 3/2026, Pasal 4 ayat (1):** pencantuman Keterangan Tidak Halal dilakukan
**secara mandiri oleh pelaku usaha** berdasarkan kriteria.

Ini temuan paling penting untuk desain agent. Artinya:

- Ada **mekanisme hukum formal** untuk menyatakan produk tidak halal — dan itu bukan
  tugas konsumen, distributor, apalagi AI.
- Maka aturan dataset "agent tidak pernah menyatakan haram tanpa bukti terdokumentasi"
  bukan sekadar kehati-hatian, tapi **sesuai pembagian kewenangan dalam regulasi**.
- Untuk Case D (CS Copilot), ini menutup celah terbesar: CS tidak boleh menjawab "haram",
  karena kewenangan itu tidak ada padanya.

---

## Temuan 4 — Kriteria teknis yang memvalidasi (dan mengoreksi) dataset

| Pasal | Isi | Efek pada dataset |
|---|---|---|
| Ps 5 | Kriteria bahan: asal hewan, asal tumbuhan, alkohol, mikroba, proses kimia/biologi/rekayasa genetika, bagian tubuh manusia, najis | Kerangka kategori di `ingredients.csv` sudah sejalan |
| Ps 7(a) | Najis mughallazhah: babi & anjing | — |
| **Ps 10(c)** | Serangga haram **kecuali** belalang, jangkrik, **cochineal**, kutu lak | ⚠️ **mengoreksi dataset**: carmine (E120) tidak otomatis kritis → diturunkan ke `SEDANG` |
| **Ps 14(b)** | Bahan tumbuhan dengan **pelarut/pengekstrak tidak halal** masuk kriteria tidak halal | ✅ memvalidasi jebakan perisa ber-etanol (BHN-04, lini FLV-ETH) |
| **Ps 15(b)** | Alkohol **≥ 0,5%** (fermentasi maupun non-fermentasi) | ✅ memberi ambang angka untuk kasus kecap & perisa |

**Implikasi:** jebakan yang saya rancang ternyata punya dasar pasal. Di pitch, kamu bisa
berkata "perisa dengan pembawa etanol kami tandai karena PerBPJPH 3/2026 Pasal 14(b)" —
itu jauh lebih kuat daripada "menurut kami berisiko".

---

## Temuan 5 — KOREKSI: ada pencarian sertifikat publik (bukan API, tapi bisa diakses mesin)

> **Koreksi atas versi pertama laporan ini.** Versi awal menyimpulkan "tidak ada sumber
> data publik" karena hanya memeriksa `ptsp.halal.go.id` (portal login untuk pemohon).
> Ternyata ada layanan terpisah: **`bpjph.halal.go.id/cari/sertifikat`** — pencarian
> publik tanpa login. Kesimpulan awal salah dan sudah diperbaiki di bawah.

### Apa yang benar-benar tersedia

| Aspek | Kenyataan |
|---|---|
| URL | `https://bpjph.halal.go.id/cari/sertifikat?produk=&produsen=&no_regis=&page=` |
| Login | **Tidak perlu** |
| Parameter | nama produk · nama pelaku usaha · nomor sertifikat · halaman |
| Akses mesin | **Bisa** — halaman di-render server-side; `curl` tanpa JS sudah mengembalikan data |
| Format | JSON ter-embed di payload RSC Next.js, **10 record per halaman** + metadata paginasi (`totalItems`, `totalPages`) |
| Field per record | nama produk, merek dagang, pelaku usaha, NIB, alamat/kab/provinsi pabrik, nomor sertifikat, **tanggal terbit**, skala usaha, kode jenis produk, foto produk |
| Barcode | **Tidak ada** |
| Komposisi bahan | **Tidak ada** |
| Tanggal berlaku / kedaluwarsa | **Tidak ada** — hanya tanggal terbit |

Klien siap pakai: `engine/bpjph_client.py` (cache + jeda 1,5 detik, batas 5 halaman per panggilan).

### KOREKSI KEDUA: database ini LUAS, bukan berisik

> Versi sebelumnya menyimpulkan "database berisik / merek besar tidak ditemukan". Itu **salah**,
> dan penyebabnya dua bug di klien saya: (1) parser JSON rusak pada nama produk yang mengandung
> tanda kutip (`Batagor indomie "Djuanda"`), sehingga hasil terbaca kosong; (2) saya menilai
> kualitas data dari **halaman 1 saja** dari hasil pencarian kata tunggal. Sudah diperbaiki.

Diuji ulang 28 Oktober 2026 (angka = `totalItems` dari respons):

| Kueri | Total | Catatan |
|---|---|---|
| `keripik` | **398.915** | pencarian substring, bukan jumlah SKU keripik sesungguhnya |
| `sambal` | **189.020** | idem |
| `indomie` | **8.840** | |
| `indomie` + produsen `indofood` | **3.252** | presisi tinggi: PT Indofood CBP |
| `aqua` | **2.926** | campuran: air minum, humancare, menu, kemasan |
| `aqua` + produsen `tirta` | **74** | presisi: PT Tirta Investama |
| `wardah` | **1.798** | campuran: kosmetik, tube kemasan |
| `wardah` + produsen `paragon` | **1.331** | presisi: PT Paragon Technology |
| `no_regis=ID1311...` | **7 produk** | satu sertifikat → banyak SKU (memvalidasi mekanika dataset) |

**Pelajaran metodologis:** pencarian bersifat *substring* lintas field. Kata tunggal menghasilkan
himpunan besar yang bercampur; presisi datang dari **kombinasi `produk` + `produsen`**. Jadi
"aqua sebagai air minum" dan "aqua sebagai produk perawatan" **bisa dipisahkan** — bukan dengan
memilih halaman lain, tetapi dengan menambahkan filter produsen.

Kode jenis produk ada (`A0014` keripik, `A0016` kopi, `H0007` tube), tetapi taksonominya tidak
terdokumentasi dan tidak konsisten — entri bernama "Kemasan Pangan ..." bisa berkode `A0005`.
Filter jenis hanya bisa mempersempit, bukan menjamin.

**Kesimpulan operasional:** sumber ini **cukup untuk "apakah produk ini terdaftar?"** dengan
presisi tinggi bila disertai nama produsen, dan **tetap tidak cukup untuk "apakah produk ini
halal?"** — karena tidak ada komposisi dan tidak ada masa berlaku.

**Implikasi langsung:**

| Rencana | Status |
|---|---|
| Cek apakah produk terdaftar (nama + produsen / nomor sertifikat) | ✅ Bisa, presisi, sudah diimplementasikan |
| Cek apakah merek X punya sertifikat (tanpa filter produsen) | ⚠️ Bisa, tapi hasil bercampur — wajib disambiguasi |
| Scan barcode → status halal | ❌ Tidak ada field barcode; tetap butuh pemetaan sendiri |
| OCR komposisi → putuskan halal/tidak | ❌ Tetap tidak boleh — keputusan bukan di lapisan itu |
| Cek masa berlaku sertifikat | ❌ Tidak diekspos |
| Klaim "produk X halal" hanya karena muncul di pencarian | ❌ **Berbahaya** — substring match bisa menangkap kemasan atau menu |

---

## Temuan 6 — Lanskap aplikasi

Aplikasi konsumen "scan barcode cek halal" sudah ada (mis. Halal Barcode, Halal Scanner,
Halal Finder) — umumnya berbasis database yang diisi manual atau komunitas, dan tidak
terhubung ke SIHALAL.

**Celahnya:** hampir semua bermain di sisi **konsumen** (B2C), sementara beban kepatuhan
sebenarnya ada di **pelaku usaha** (B2B) — dan di situ belum ada alat yang menyambungkan
registri sertifikat, sertifikat pemasok, dan label.

---

## Temuan 6b — PP 40/2026: kewajiban sertifikasi ditunda, bukan dibatalkan

**PP No. 40 Tahun 2026** mengubah PP 42/2024 dan menyesuaikan masa penahapan kewajiban
sertifikasi halal (sumber: siaran BPJPH, 2026).

| Kelompok produk | Kewajiban mulai |
|---|---|
| Makanan/minuman/sembelihan — **usaha menengah & besar** | **18 Okt 2024** (tidak berubah) |
| Makanan/minuman/sembelihan — **usaha mikro & kecil (UMK)** | **17 Okt 2028** (ditunda) |
| Jasa terkait makanan (selain jasa penyembelihan), menengah & besar | 17 Okt 2028 |
| Makanan/minuman **dari luar negeri (impor)** | **18 Okt 2028** |
| Obat bahan alam, kuasi, suplemen, kosmetik, kimiawi, rekayasa genetika, barang gunaan (sandang, rumah tangga, dll.) | 17 Okt 2028 |
| Obat bebas & bebas terbatas, alkes risiko B | 17 Okt 2029 |
| Obat keras (kec. psikotropika), alkes risiko C | 17 Okt 2034 |

**Konsekuensi untuk produk kita:** mayoritas isi database BPJPH adalah UMK (self-declare),
dan kewajiban mereka baru berlaku 2028. Artinya **"tidak ditemukan di database" adalah
kondisi normal**, bukan anomali. Ini memperkuat aturan: tidak ditemukan ≠ tidak halal.

---

## Temuan 6c — Lokasi produksi ADA, distribusi TIDAK ADA

Record BPJPH memuat `pabrik[]` dengan alamat lengkap sampai kelurahan/kecamatan, plus
`kab_kota`, `provinsi`, `kode_pos`, `negara`. Kode wilayah mengikuti BPS
(mis. `13` = Sumatera Barat, `1304` = Tanah Datar — cocok dengan alamat "TABEK PATAH KEC.
SALIMPAUNG"). Untuk produk impor, field `provinsi` berisi nama (mis. "Pathum Thani").

| Pertanyaan | Bisa dijawab? | Dasar |
|---|---|---|
| Produk ini diproduksi di mana? | ✅ **Ya**, presisi alamat | `pabrik[].alamat`, `kab_kota`, `provinsi` |
| Ini produk lokal atau impor? | ✅ **Ya** | field `negara` |
| Siapa produsennya & skala usahanya? | ✅ **Ya** | `pelaku_usaha`, `skala_usaha` |
| Produk ini dipasarkan/distribusi ke mana? | ❌ **Tidak** | tidak ada field distribusi |
| Produk halal apa saja di toko A? | ❌ **Tidak** | butuh data inventori ritel, domain lain |
| Daftar semua produsen halal di kecamatan X | ⚠️ **Tidak praktis** | endpoint hanya pencarian kata kunci, tanpa filter wilayah; butuh crawl seluruh DB |

Diimplementasikan: `engine/bpjph_client.py` mode `asal` (termasuk peta 38 kode provinsi).

**Kesimpulan:** sertifikat halal adalah **dokumen kepatuhan**, bukan catatan rantai pasok.
Pertanyaan "dipasarkan ke mana" adalah pertanyaan **distribusi/ritel**, dan tidak akan
ditemukan di domain halal — seberapa keras pun dicari.

## Temuan 7 — Pertanyaan yang belum terjawab

| Pertanyaan | Status | Dampak |
|---|---|---|
| Masa berlaku sertifikat: 4 tahun, atau selama tidak ada perubahan? | **Tidak terverifikasi** — sumber saling bertentangan | Sedang. Dataset memakai asumsi konservatif (gugur bila komposisi/pemasok berubah), aman di kedua rezim |
| Tenggat kewajiban bertahap per kategori | ✅ **Terjawab** — PP 40/2026 (lihat Temuan 6b) | — |
| Apakah ada akses data publik | ✅ **Terjawab** — pencarian publik ada, tanpa API resmi (Temuan 5) | — |
| Apakah ada data distribusi/penjualan | ✅ **Terjawab** — tidak ada di domain halal (Temuan 6c) | — |

**Rekomendasi:** jangan jadikan "masa berlaku" sebagai klaim utama di pitch. Pakai
**change-triggered invalidation** — itu benar di kedua rezim dan lebih mudah didemokan.

---

## Peta temuan → keputusan produk

| Temuan | Case A (Watchtower) | Case D (CS Copilot) |
|---|---|---|
| Sanksi sampai penarikan barang | Nilai jual: cegah penarikan, bukan cuma audit | Kalimat eskalasi ke Halal Center |
| "Tidak halal" = kewenangan pelaku usaha | Status engine tidak pernah menuduh | CS tidak pernah menulis "haram" |
| Ps 14(b), 15(b) | Titik kritis punya dasar pasal | Penjelasan ke pelanggan tetap tanpa jargon |
| Data tidak terbuka | Fokus ke registri internal | Jangan janjikan verifikasi pihak ketiga |
| Kompetitor B2C | Diferensiasi B2B | — |

---

## Sumber

1. Peraturan BPJPH No. 2 Tahun 2026 — Pengenaan Sanksi Administratif.
   <https://peraturan.bpk.go.id/Details/357399>
2. Peraturan BPJPH No. 3 Tahun 2026 — Bentuk dan Tata Cara Pencantuman Keterangan Tidak Halal.
   <https://peraturan.bpk.go.id/Details/357401>
3. Peraturan BPJPH No. 1 Tahun 2025 — Satu Data BPJPH.
   <https://peraturan.bpk.go.id/Details/345998>
4. Peraturan BPJPH No. 5 Tahun 2025 — Kriteria UMKM.
   <https://peraturan.bpk.go.id/Details/346004>
5. Peraturan BPJPH No. 7 Tahun 2025 — Komite Fatwa Produk Halal.
   <https://peraturan.bpk.go.id/Details/346009>
6. SIHALAL (portal login pemohon): <https://ptsp.halal.go.id/>
7. **Pencarian sertifikat publik BPJPH** (diuji langsung 28 Okt 2026):
   <https://bpjph.halal.go.id/cari/sertifikat> — klien di `engine/bpjph_client.py`

Teks PDF tersimpan di `research/src/` untuk verifikasi ulang.

> **Catatan penggunaan:** angka dan pasal di atas sudah dibaca dari teks resmi, tetapi
> regulasi dapat berubah. Sebelum dipakai di materi publik atau demo, cek ulang ke JDIH.
> Jangan mengutip nomor pasal untuk hal yang tidak ada di dokumen ini.
