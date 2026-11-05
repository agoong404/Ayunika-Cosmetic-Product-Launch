# Accountability Sheet — Ayunika Content Reviewer

> **Challenge C — The Creator Agent** · Skenario: peluncuran produk (bodycare/beautycare)
> Tim 3 agent: Planner · Writer · **Reviewer** · Tanggal: 31 Okt 2026
>
> Setiap klaim di bawah punya bukti yang bisa dijalankan: `engine/run_reviewer_tests.py`
> (**73/73 lulus**), `engine/pipeline.py` (siklus penuh), `engine/audit_kemasan.py`,
> `engine/governance.py verify`.

---

## Kuadran 1 — Apa yang BISA diakses agent

| Sumber | Cakupan | Batas |
|---|---|---|
| Lembar produk | 4 SKU: fakta, bahan, harga, nomor BPOM, status halal | Satu-satunya sumber fakta. Writer dilarang menambah fakta (R-11) |
| Rulebook | R-01..R-21 | Dasar penolakan; tiap tolakan wajib kutip nomor + kalimat |
| Brief kampanye | BRF-101 | Memuat 5 klaim yang **tidak boleh** dipakai apa adanya |
| Nada merek & spesifikasi platform | tone guide, 3 platform | Batas karakter, hashtag, emoji |
| Registri sertifikat internal | `products.csv` + `certificates.csv` | Menentukan status halal per SKU |
| **Registri legalitas** | `izin_edar.csv`, `izin_produksi.csv`, `sertifikat_klaim.csv` | Menentukan boleh-tidaknya klaim "terdaftar BPOM", "pabrik tersertifikasi", "organik", "dermatologically tested" |
| **Komposisi & batas pengawet** | `komposisi_produk.csv`, `batas_pengawet.csv` | Dasar R-21: kadar pengawet vs batas per bahan |
| **Registri publik BPJPH** | `bpjph.halal.go.id` | **Hanya verifikasi keberadaan nomor**, bukan penentu status |

## Kuadran 2 — Apa yang dijalankan SECARA OTONOM

| Aksi | Kondisi |
|---|---|
| Planner menyusun kerangka per platform | Otonom, hanya dari brief + lembar produk |
| Writer menulis & memperbaiki draf | Otonom, hanya fakta dari lembar produk |
| Reviewer menilai draf terhadap R-01..R-21 | Otonom, setiap draf, tanpa berhenti di temuan pertama |
| Audit kemasan & komposisi (pra-konten) | Otonom — `audit_kemasan.py` memeriksa izin, label, dan batas pengawet |
| Validasi teks pada aset gambar | Otonom — `validate_asset.py` merender kartu, membaca ulang lewat OCR, lalu menolak bila angka atau teks tidak cocok dengan lembar produk |
| Reviewer **menurunkan** hasil (TOLAK) | Otonom — arah aman selalu menolak |
| Reviewer **meloloskan** (LOLOS) | Otonom **hanya bila nol temuan**; tidak ada override |
| Menulis log & riwayat revisi | Otonom, setiap tahap, hash-chain |

## Kuadran 3 — Apa yang WAJIB approval manusia

| Aksi | Siapa menyetujui | Bukti |
|---|---|---|
| **Publikasi konten** (TikTok/IG/marketplace) | Marketing Lead | `plan_id` APPROVED + entri log `execute` |
| Mengubah/menambah aturan rulebook | Regulatory Affairs | plan + log |
| Mengecualikan aturan (waiver) | Regulatory + Marketing Lead | plan + log, alasan tercatat |
| **Eskalasi** setelah 3 iterasi | Regulatory Affairs | log `escalate` + daftar sisa masalah |

Gerbang menolak plan berstatus PROPOSED, menolak **self-approval**, dan token **sekali pakai**.

## Kuadran 4 — Apa yang TIDAK AKAN PERNAH dilakukan agent

1. Menerbitkan konten tanpa `plan_id` berstatus APPROVED.
2. Menulis klaim halal untuk produk yang sertifikatnya tidak aktif / tidak mencakup SKU.
3. Menyatakan produk **haram** — bukan kewenangannya, dan tidak ada bukti.
4. Memakai superlatif/janji hasil ("terbaik", "dijamin", "dalam 3 hari", "permanen").
5. Menyebut "memutihkan"/"whitening" — hanya "mencerahkan".
6. Mengarang pelanggaran: temuan tanpa kutipan yang ada di draf **dibuang otomatis**.
7. Berputar tanpa henti: maksimal 3 iterasi, lalu eskalasi.
8. Menyalin fakta dari luar lembar produk, termasuk dari brief bila brief salah.

## Mekanisme Penegakan

Reviewer berjalan **dua lapis**. Lapis deterministik (kode) memeriksa hal yang tidak butuh
selera: klaim halal terhadap registri sertifikat (R-03), frasa terlarang, angka terhadap
lembar produk (R-06), disclaimer, emoji, batas platform. Lapis penilaian (model) menangani
nada dan akurasi parafrase — tetapi **setiap temuannya wajib mengutip teks yang benar-benar
ada di draf**; kutipan yang tidak ditemukan dibuang sebelum masuk laporan, sehingga model
tidak bisa mengarang pelanggaran. Wewenang lapis model juga dibatasi enam aturan
(R-04, R-05, R-07, R-08, R-10, R-12); temuan di luar itu ditolak agar ia tidak mengulang
pekerjaan kode. Setiap temuan yang dibuang dicatat beserta alasannya, bukan dihilangkan. Loop dikendalikan `decide_next()`: `LOLOS` → approval,
`TOLAK` → Writer, dan pada iterasi ke-3 tetap gagal → `ESKALASI` beserta sisa masalah.
Semua tahap ditulis ke audit log append-only ber-hash-chain, sehingga urutan
plan → draf → tolakan → revisi → persetujuan dapat diaudit ulang baris per baris.

## Keterbatasan yang Diketahui

- **Nomor sertifikat produk Ayunika adalah MOCK.** Tidak akan ditemukan di BPJPH. Verifikasi
  eksternal hanya dipakai untuk mendemokan mekanismenya, bukan untuk membuktikan produk kita.
- **Lapis model sudah tersambung, tapi belum diuji dengan provider sungguhan.** Jalurnya ada
  dua: jembatan WorkBuddy (`agents/workbuddy.py`, tanpa API key) dan adapter HTTP
  (`agents/llm/client.py`). Yang terbukti baru *jalurnya* — 12 asersi dengan klien palsu —
  bukan kualitas keluaran model nyata. Uji dengan 5–10 draf nyata sebelum mengklaim akurasi.
- **Lapis model bisa melewatkan, bukan hanya salah.** Contoh nyata: frasa "paling banyak
  diteliti" lolos dari kode (R-07 adalah daftar kata, bukan konsep) dan hanya tertangkap
  lapis model. Artinya recall lapis-2 bergantung pada prompt dan pada model yang dipakai.
- **Planner & Writer kini ada di `agents/`** dengan dua mode (model / deterministik). Mode
  deterministik sengaja konservatif — ia menyalin klaim yang diizinkan, jadi hampir selalu
  lolos di iterasi pertama. Nilai sesungguhnya baru muncul saat mode model dipakai.
- **62 asersi uji di sini fokus ke Reviewer.** Dataset resmi Challenge C punya 20 kasus untuk
  sistem penuh — keduanya perlu direkonsiliasi agar tidak ada dua angka "20/20" berbeda arti.
- **Rulebook memakai nomor internal (R-xx).** Kolom dasar menyebut jenis regulasi, bukan pasal.
  Verifikasi ke Peraturan BPOM tentang Klaim Kosmetika sebelum materi publik.
- **Kewajiban halal kosmetik baru 17 Okt 2028** (PP 40/2026). Produk tanpa sertifikat bukan
  pelanggaran; **mengklaim** halal tanpa sertifikat tetap pelanggaran.
