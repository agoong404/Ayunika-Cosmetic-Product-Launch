# Panduan Update UI/UX — Lolos (siap integrasi ke repo)

> **Dibuat:** 7 November 2026, lewat sesi Claude Code (WorkBuddy) terpisah dari repo.
> **Revisi:** 7 November 2026 — 4 perbaikan UI (§2.1 baris bertanda **[Revisi]**): tombol CTA
> besar di Beranda, unggah↔dropdown bolak-balik, opsi sudut disamakan persis dengan
> `web/server/index.js` asli, kontrol konsol diperbesar.
> **Status:** paket siap integrasi. Belum disentuh ke repo `Ayunika-Cosmetic-Product-Launch`
> — pemilik repo yang akan eksekusi merge & deploy.
> **Target:** `web/public/` (frontend) dan `web/server/index.js` (BFF) di repo utama.

---

## 0. Ringkasan satu layar

| Bagian | Isi | Status |
|---|---|---|
| §1 Alur baru | 11 langkah marketer + alasan tiap keputusan | Rancangan final |
| §2 Frontend | `public/app.js`, `public/styles.css` — sudah diupdate di sini | **Siap salin ke `web/public/`** |
| §3 Backend | 2 endpoint baru (`upload-produk`, `run-relay`) — kode siap tempel | **Siap tempel ke `web/server/index.js`** |
| §4 Uji lokal | Cara jalankan tanpa MCP sungguhan | **Sudah diuji, jalan** |
| §5 Dokumen PDF | 4 "Lembar Produk" untuk uji fitur unggah | Sudah ada, siap pakai |
| §6 Belum bisa ditangani dari sini | Daftar hal yang butuh cek expert agent / kredensial asli | Lihat sebelum merge |
| §7 Checklist integrasi | Urutan kerja disarankan | — |

---

## 1. Alur baru & alasan desainnya

### 1.1 Sebelas langkah

| # | Langkah | Catatan |
|---|---|---|
| 1 | Buka situs | tidak berubah |
| 2 | **Unggah dokumen profil produk (PDF)** atau pilih dari dropdown (fallback) | **BARU** — lihat §1.2 |
| 3 | Pilih platform (TikTok/Instagram/marketplace) | tidak berubah |
| 4 | Pilih bahasan utama (tombol sudut cerita) | label diperjelas jadi "Pilih bahasan utama yang ingin dibuat konten" |
| 5 | Submit → `run_cycle`-setara | endpoint pindah ke `/api/run-relay` |
| 6–9 | Output **per agent**: Bima (rencana) → Citra (draf tiap iterasi) → Dimas (verdict+temuan tiap iterasi) | draf per iterasi sekarang **benar-benar tampil**, sebelumnya kosong diam-diam |
| 10 | LOLOS → tombol "Ajukan Approval" | tidak berubah, tetap tanpa tombol setuju |
| 11 | TOLAK → bukti penolakan (aturan+kutipan+perbaikan) | tidak berubah |

### 1.2 Kenapa dokumen upload, bukan sekadar dropdown

**Prinsip yang WAJIB dipegang kalau fitur ini diteruskan:**

> **Dokumen = pengenal produk, bukan sumber fakta baru.**

Backend hanya membaca **SKU** (dan `doc_id` opsional) dari header dokumen, lalu menarik
ulang semua fakta (harga, BPOM, status sertifikat) dari `products.csv`/`certificates.csv`
di server — **persis seperti jalur dropdown**. Isi fakta lain di dalam PDF (komposisi,
keterangan kemasan) **tidak pernah** dibaca atau dipercaya sebagai data baru.

Alasan: begitu dokumen ada di tangan pengguna, isinya bisa diedit sebelum diunggah ulang.
Kalau sistem memercayai teks di file sebagai fakta, pengguna bisa menulis klaim halal/BPOM
palsu dan sistem akan menerimanya — bertentangan dengan aturan akuntabilitas **Sources**
(lihat `panduan-challenge-c/02_lima_aturan_akuntabilitas.md` di root folder Hackathon).

**Dropdown tetap ada sebagai fallback** — kalau parsing dokumen gagal (format aneh, SKU
tidak terbaca), pengguna tidak terjebak; cukup klik "pilih dari daftar produk".

### 1.3 Kenapa `/api/run-relay`, bukan tetap `/api/run`

`run_cycle()` (dipanggil `/api/run` yang ada sekarang) **tidak menyimpan teks draf per
iterasi** — dicek langsung di `mcp_server/tools.py:472-483`: tiap entri `riwayat` cuma
punya `iterasi`, `verdict`, `jumlah_temuan`, `aturan`, `temuan`. Jadi sebelumnya UI tidak
bisa menampilkan "Citra menulis apa di iterasi 1" — field `draf` yang sudah dirujuk di
`app.js` lama **selalu kosong diam-diam**.

`/api/run-relay` (baru, §3.2) memanggil tool yang **sama persis** yang dipanggil
`run_cycle()` secara internal (`plan_content` → loop `write_draft`+`review_draft`), hanya
menyimpan draf-nya juga. **Tidak ada perubahan** di `mcp_server/` atau `engine/` — murni
"membuka" apa yang sudah ada.

---

## 2. Perubahan frontend (sudah dikerjakan di sini)

File yang diubah di folder ini (`ayunika-ui/ayunika-ui/public/`) — **salin isi folder
`public/` ini ke `web/public/` di repo**, timpa yang lama:

### 2.1 `app.js`

| Bagian | Baris kira-kira | Apa yang berubah |
|---|---|---|
| Komentar header | 1-5 | Catat endpoint baru yang dipakai |
| State modul | ~200-205 | `skuTerpilih`, `namaProdukTerpilih` — menyimpan SKU aktif dari unggahan/dropdown |
| `viewConsole()` | ~207-259 | Markup baru: area unggah (`#upload-area`, `#file-pdf`) di atas dropdown SKU yang kini **tersembunyi default** (`#controls-sku`); label sudut diperjelas |
| `viewConsole()` — CTA Beranda | **[Revisi]** `viewBeranda()` | Tombol "Coba Review" dipisah ke `.cta-center` + class `.btn.big` (besar, center, bayangan warna brand); "Lihat Tim Agent" jadi baris terpisah di bawahnya, bukan sejajar |
| `setupUpload()` (fungsi baru) | ~264-333 | Validasi file (tipe PDF, maks 2MB) → `fetch("/api/upload-produk")` → simpan `skuTerpilih` → tampilkan nama produk dikenali. Tombol "pilih dari daftar produk" membuka dropdown fallback dan melepas `skuTerpilih` |
| `setupUpload()` — toggle balik | **[Revisi]** | Tombol baru `#tombol-unggah` ("↑ unggah dokumen sebagai gantinya") di dalam `#controls-sku` — dropdown bisa kembali ke mode unggah, bukan cuma satu arah |
| `runLive()` | — | Pakai `skuTerpilih \|\| document.getElementById("sku").value`; endpoint pindah ke `/api/run-relay`; validasi "pilih produk dulu" kalau belum ada SKU sama sekali |
| `renderRelay()` — langkah Rani | — | Judul sekarang menampilkan nama produk (`ctx.nama`), bukan cuma SKU mentah, kalau tersedia |

**Yang TIDAK diubah** (sengaja): `renderRelay()` untuk langkah Bima/Citra/Dimas, `playDemo()`,
alur approval (`ajukan()`, `pollStatus()`), halaman Beranda/Agents/Audit — semua tetap jalan
seperti sebelumnya karena bentuk data `plan`/`riwayat` dari `/api/run-relay` **sama** dengan
yang diharapkan kode lama (`riwayat[].draf` memang sudah dirujuk, cuma sekarang benar-benar terisi).

### 2.1.1 Opsi sudut cerita — **wajib sama persis dengan backend** **[Revisi]**

`loadAngles()` di `app.js` **tidak hardcode** label/teks sudut — selalu mengambil dari
`GET /api/sudut`, jadi frontend otomatis ikut apa pun yang dikembalikan BFF. Yang perlu
dijaga adalah **BFF-nya sendiri** (`web/server/index.js`, `SUDUT_PILIHAN`, sudah ada di
repo — **tidak diubah** di paket ini) dan **mock lokal** (`preview-server.js`, §4) —
keduanya harus memuat 4 pilihan yang sama persis:

| label | angle |
|---|---|
| bahan aktif | Jelaskan bahan aktif dan kadarnya |
| tekstur ringan | Tekankan tekstur ringan dan cepat meresap |
| kulit kusam | Ditujukan untuk kulit kusam |
| promo peluncuran | Sebutkan promo peluncuran dan kuotanya |

`preview-server.js` di paket ini sudah disamakan persis (sebelumnya sempat beda — mock
lama pakai label "Manfaat utama"/"Kandungan aktif"/"Harga & promo" yang **tidak match**
backend asli; kalau tidak disamakan, `/api/run` sungguhan menolak dengan `PESAN_TOLAK`
karena `angle` tidak ada di daftar sahnya). Tidak ada perubahan yang dibutuhkan di BFF asli
untuk poin ini — hanya pengingat agar siapa pun yang mengedit `SUDUT_PILIHAN` di `index.js`
nanti juga mengedit `preview-server.js` di sini supaya pratinjau lokal tetap representatif.

### 2.1.2 Ukuran kontrol konsol **[Revisi]**

`styles.css` — dropdown, label, tombol sudut (`.chip-btn`), dan tombol aksi (`#run-btn`,
`#demo-btn`) diperbesar (padding & `font-size` naik) dibanding bagian situs lain, supaya
mudah dilihat/dipakai saat demo di proyektor atau layar kecil. Area unggah (`.upload-area`)
juga diperbesar (border lebih tebal, padding lebih luas).

### 2.2 `styles.css`

Tambahan kecil sebelum blok `.controls` yang sudah ada: `.upload-area`, `.upload-label`,
`.upload-prompt`, `.link-btn`, `.upload-status` (+ varian `.ok`/`.error`). Tidak mengubah
style yang sudah ada.

### 2.3 Yang tidak disentuh

`index.html`, `data/agents.js`, `data/demo.js`, `assets/avatars/*` — tidak ada perubahan,
karena markup konsol dirender dinamis dari `app.js`, dan profil agent/replay tidak terpengaruh
oleh fitur upload.

---

## 3. Backend yang disiapkan (folder `backend-patch/`)

**Belum ada di repo** — ini kode baru yang perlu ditempel manual ke
`web/server/index.js`. Tidak ada perubahan di `mcp_server/` atau `engine/`.

### 3.1 `backend-patch/upload-produk.route.js`

Endpoint `POST /api/upload-produk`:
1. Baca body sebagai buffer biner (PDF), maks 2MB.
2. Ekstrak teks pakai `pdf-parse` (lihat §3.3 — **versi API penting**).
3. Cari SKU dengan regex `SKU[\s\n]+(AY-[A-Z]{2}-\d{3})` dari header dokumen.
4. Validasi SKU ke `list_products` (data asli server) — **isi PDF lain tidak pernah dibaca**.
5. Balas `{ ok, sku, doc_id, sisa_jatah }`.

Cara pasang: lihat komentar di bagian atas file — tempel blok `if (...)` ke dalam
`tanganiApi()` di `index.js`, tambah `BATAS.upload`, tambah import `PDFParse`.

### 3.2 `backend-patch/run-relay.route.js`

Endpoint `POST /api/run-relay`: memanggil `plan_content` → loop `write_draft`+`review_draft`
(maks 3 iterasi) — identik dengan isi `run_cycle()` di `mcp_server/tools.py`, hanya
menyimpan `draf` di tiap entri `riwayat`. Gaya kode (nama fungsi `bacaJson`, `kirim`,
`cekSku`, `cekPlatform`, `BATAS`, `boleh()`, `SUDUT_PILIHAN`, `PESAN_TOLAK`) **dicocokkan**
dengan `web/server/index.js` yang sudah ada — tinggal tempel, tidak perlu menulis ulang gaya.

### 3.3 Dependency baru: `pdf-parse` — **catatan penting versi**

BFF sebelumnya **nol dependensi** (`web/package.json` dicek langsung: `"description":
"...Tanpa dependensi."`). Ini jadi dependency npm pertama.

**Temuan saat menyiapkan ini:** `npm install pdf-parse` hari ini menarik **v2.4.5**, yang
API-nya **berbeda total** dari v1.x yang umum direferensikan di tutorial lama:

```js
// v1.x (LAMA, TIDAK DIPAKAI DI SINI):
const data = await pdfParse(buffer);
console.log(data.text);

// v2.x (DIPAKAI DI upload-produk.route.js INI):
const parser = new PDFParse({ data: buffer });
const { text } = await parser.getText();
await parser.destroy();
```

Kode di `upload-produk.route.js` **sudah pakai API v2** dan **sudah diuji nyata** —
lihat §3.4. Kalau nanti `npm install` menarik versi lain, jalankan ulang skrip uji
sebelum percaya kodenya masih jalan.

### 3.4 Verifikasi nyata (bukan asumsi)

Skrip `backend-patch/test-pdf-extract.mjs` membaca 4 PDF di
`dataset_c/product_profile_pdf/` dan menguji regex SKU/doc_id. Hasil run (7 Nov 2026):

```
OK   PS-101_Ayunika_Bright_Serum_LembarProduk.pdf -> sku=AY-SR-101 doc_id=PS-101
OK   PS-102_Ayunika_Glow_Body_Lotion_LembarProduk.pdf -> sku=AY-BL-102 doc_id=PS-102
OK   PS-103_Ayunika_Gentle_Cleanser_LembarProduk.pdf -> sku=AY-FW-103 doc_id=PS-103
OK   PS-104_Ayunika_Coffee_Scrub_LembarProduk.pdf -> sku=AY-SC-104 doc_id=PS-104
Semua file cocok.
```

Jalankan ulang kapan saja: `cd ayunika-ui/ayunika-ui && npm install && node backend-patch/test-pdf-extract.mjs`

### 3.5 `backend-patch/package.json.patch.txt`

Baris yang perlu ditambah ke `web/package.json` + catatan versi di atas.

---

## 4. Uji lokal tanpa MCP (sudah diuji jalan)

`preview-server.js` (di folder ini) menyajikan `public/` dan memalsukan `/api/*` dengan
data contoh — **kecuali `/api/upload-produk`, yang memakai `pdf-parse` SUNGGUHAN** (bukan
mock) supaya pengujian unggah dokumen representatif terhadap backend asli nanti.

```bash
cd ayunika-ui/ayunika-ui
npm install            # menarik pdf-parse
node preview-server.js # http://localhost:8099
```

**Sudah diuji end-to-end di sesi ini:**
- Buka `http://localhost:8099` → halaman termuat.
- Unggah salah satu PDF dari `dataset_c/product_profile_pdf/` lewat `curl` ke
  `/api/upload-produk` → `{"ok":true,"sku":"AY-SR-101","doc_id":"PS-101",...}`.
- `/api/run-relay` dengan SKU itu → mengembalikan `plan` + `riwayat[].draf` terisi.
- SKU asing (`AY-ZZ-999`) → `PERLU_DATA`, bukan error atau LOLOS palsu.
- `/api/propose` → dapat `plan_id`, alur approval tetap jalan.
- **[Revisi]** `GET /api/sudut` → 4 opsi persis sama dengan `SUDUT_PILIHAN` di
  `web/server/index.js` asli (§2.1.1); `/api/run-relay` dengan salah satu `angle`
  persis itu diterima (tidak kena `PESAN_TOLAK`).
- **[Revisi]** Tombol "↑ unggah dokumen sebagai gantinya" di dropdown fallback
  mengembalikan ke mode unggah dan membersihkan status sebelumnya.

**Bukan untuk deploy** — hanya alat pratinjau. Hapus `preview-server.js` dan
`backend-patch/test-pdf-extract.mjs` saat merge ke repo utama (keduanya alat developer,
bukan bagian situs — lihat juga `NOTES.md` §8 soal ini, poin lama yang masih berlaku).

---

## 5. Dokumen PDF untuk uji fitur unggah

4 "Lembar Produk" sudah dibuat di `dataset_c/product_profile_pdf/` (repo utama, bukan di
folder ini) — isi: Informasi Produk, Komposisi, Keterangan Kemasan saja (tanpa klaim
boleh/dilarang — itu tetap di `dataset_c/product_sheets/*.md` internal). Juga sudah
diunggah ke Google Drive folder "Hackathon" sebagai referensi terpisah.

> **Catatan kebersihan repo:** ada folder lama `dataset_c/product_sheets_pdf/` (versi
> lengkap dengan klaim, dibuat sebelum revisi) — **bukan** yang dipakai fitur ini. Hapus
> atau beri label jelas sebelum merge supaya tidak tertukar.

---

## 6. Yang BELUM bisa ditangani dari sesi ini — cek ke expert agent

Sesi ini **tidak punya akses** ke `MCP_URL`/`MCP_TOKEN` asli, ke sesi WorkBuddy Ayunika
Compliance Team yang sesungguhnya, atau ke proses deploy Railway. Hal-hal berikut perlu
diverifikasi oleh pemilik repo / lewat expert agent WorkBuddy sebelum merge:

1. **Uji `/api/run-relay` terhadap MCP live sungguhan.** Kode di sini hanya diverifikasi
   lewat mock lokal (pdf-parse-nya nyata, tapi `plan_content`/`write_draft`/`review_draft`
   dipalsukan di `preview-server.js`). Jalankan dulu lewat `curl` ke BFF beneran sebelum
   percaya penuh.
2. **Cek apakah MCP server punya rate limit per sesi/IP** yang bisa kena di pola panggilan
   beruntun `/api/run-relay` (sampai 7 panggilan tool per satu klik "Jalankan review":
   1 `plan_content` + hingga 3×`write_draft`+`review_draft`). Tidak terlihat di
   `mcp_server/tools.py` yang sempat dibaca, tapi belum dicek `mcp_server/server.py`
   transport layer secara menyeluruh.
3. **Minta WorkBuddy/expert agent review ulang apakah regex SKU** (`SKU[\s\n]+(AY-[A-Z]{2}-\d{3})`)
   cukup tahan terhadap variasi hasil `pdf-parse` di berbagai PDF reader/OS — pengujian di
   sini hanya dari PDF yang digenerate ReportLab sendiri (lihat `dataset_c/` scripts
   generator), belum dari PDF yang di-print-to-PDF via aplikasi lain.
4. **Sinkronkan `data/agents.js`** di `public/` kalau file `expert/ayunika-compliance-team/agents/*.md`
   berubah — tidak disentuh di sesi ini karena tidak ada perubahan pada profil agent.
5. **Update dokumen submission** (`submission_templates/02_test_results.md`,
   `07_submission_checklist.md` item 11) kalau fitur ini jadi dipakai di demo — belum
   dikerjakan di paket ini, di luar scope UI.
6. **Deploy ke Railway** dan verifikasi `/api/upload-produk` + `/api/run-relay` lewat
   domain live (`ayunika-care.web.id` atau host Railway) — sesi ini hanya menguji lokal.
7. **Keputusan: endpoint baru atau ganti `/api/run`?** Paket ini menambah `/api/run-relay`
   sebagai endpoint terpisah (tidak menghapus `/api/run` lama). Pemilik repo boleh memilih
   mengganti `/api/run` langsung kalau tidak ada klien lain yang bergantung padanya.

---

## 7. Checklist integrasi (urutan disarankan)

- [ ] 1. Hapus/label `dataset_c/product_sheets_pdf/` (§5).
- [ ] 2. `npm install pdf-parse` di `web/`, tempel §3.1 dan §3.2 ke `web/server/index.js`.
- [ ] 3. Jalankan `node backend-patch/test-pdf-extract.mjs` sekali lagi di environment
      repo utama untuk pastikan versi `pdf-parse` yang ter-install konsisten.
- [ ] 4. Salin isi `public/` (folder ini) ke `web/public/`, timpa `app.js`/`styles.css`.
- [ ] 5. Jalankan `node server/index.js` lokal dengan `MCP_URL`/`MCP_TOKEN` asli, uji
      manual: unggah PDF → jalankan review → lihat panel Bima/Citra/Dimas → ajukan approval.
- [ ] 6. Uji jalur gagal: PDF rusak, SKU tak dikenali, dokumen yang sudah diedit sebelum
      diunggah ulang (pastikan sistem tetap pakai data server, bukan isi PDF).
- [ ] 7. Hapus `preview-server.js` + `backend-patch/test-pdf-extract.mjs` sebelum commit final
      (alat developer, bukan bagian situs).
- [ ] 8. Selesaikan item §6 di atas bersama expert agent / tim sebelum deploy ke Railway.
- [ ] 9. Deploy, verifikasi dari domain live, update checklist submission bila relevan.
