# Project Description — Lolos

> **Blurb (<10 kata):** Reviewer konten peluncuran kosmetik: tolak, perbaiki, setujui.

## 1. Project Overview

**Challenge:** C — The Creator Agent
**Skenario:** Peluncuran produk (*product launch*), kategori bodycare & beautycare
**Target users:** Tim marketing UMKM/UKM kosmetik Indonesia (1–3 orang) yang menulis
sendiri konten TikTok, Instagram, dan marketplace — tanpa tim regulatory sendiri.

**Lolos** adalah sistem tiga agent (Planner · Writer · Reviewer) yang membantu tim
marketing menulis konten peluncuran produk yang **lolos aturan sebelum terbit**, dibangun
di Tencent Cloud WorkBuddy untuk Challenge C.

Yang membuatnya berbeda dari "AI penulis caption": setiap penolakan wajib menyebut
**nomor aturan, kutipan kalimat yang bermasalah, dan perbaikan konkret** — dan seluruh
siklusnya tercatat di audit log yang tidak bisa diubah diam-diam.

## 2. Real-World Insight

**Dari mana pain point-nya?** Bukan dari penulis konten yang ceroboh, tapi dari **brief**.
Di dataset kami, brief peluncuran berisi 5 pesan kunci; **4 di antaranya melanggar aturan**
— "hasilnya kelihatan dalam 7 hari" (janji hasil), "sudah halal, tinggal nunggu
sertifikatnya keluar" (klaim tanpa sertifikat), "bandingkan dengan serum kompetitor"
(merendahkan pesaing), dan testimoni "jerawatku hilang total dalam 3 hari" (klaim medis).
Tim marketing menulis dari brief itu karena brief dianggap instruksi, bukan kumpulan klaim
yang perlu diperiksa.

**Siapa yang mengalaminya?** Produsen kosmetik kecil di Indonesia menghadapi tiga rezim
sekaligus: klaim kosmetik BPOM (dilarang "memutihkan", harus "mencerahkan"), sertifikasi
halal BPJPH, dan batas platform yang berbeda-beda. Satu hal yang sering terlewat:
kewajiban sertifikasi halal untuk kosmetik baru berlaku **17 Oktober 2028** (PP 40/2026) —
jadi produk tanpa sertifikat **bukan pelanggaran**, tetapi **mengklaim** halal tanpa
sertifikat tetap pelanggaran. Hampir semua pemeriksa otomatis salah di titik ini: mereka
menolak produk yang belum bersertifikat, lalu meloloskan yang mengklaim tanpa bukti.

**Apa yang kami selesaikan?** Memisahkan "produk belum bersertifikat" (wajar) dari
"konten mengklaim halal" (pelanggaran), dan menegakkan aturan platform yang biasanya
hanya jadi lampiran dokumen — misalnya hashtag `#halal` dihitung sebagai klaim, dan
listing marketplace wajib mencantumkan nomor BPOM.

## 3. Solution Design

### 3a. Arsitektur bisnis

- **Sebelum:** copywriter menulis draf → atasan membaca sekilas → terbit. Pemeriksaan
  klaim bergantung pada ingatan satu orang. Biayanya muncul belakangan: konten ditarik,
  atau klaim halal terlanjur tersebar tanpa sertifikat.
- **Sesudah:** brief masuk → Planner menyusun kerangka (fakta mana yang boleh dipakai) →
  Writer menulis → Reviewer menilai dua lapis → bila ditolak, Writer memperbaiki dengan
  catatan spesifik → maksimal 3 putaran → **manusia menyetujui** sebelum terbit.
  Manusia tidak lagi mencari kesalahan; ia memutuskan pada pilihan yang sudah disaring.

### 3b. Arsitektur teknis

- **Lima sumber masukan:** brief, lembar produk (satu-satunya sumber fakta), rulebook
  R-01..R-21, panduan nada merek, spesifikasi platform.
- **Reviewer dua lapis, sengaja dipisah.** Lapis kode memeriksa yang berbentuk pola:
  harga dan angka (R-06), klaim halal terhadap registri sertifikat (R-03), frasa terlarang,
  disclaimer, emoji, batas platform, kuota promo. Lapis model hanya menilai yang butuh
  pemahaman bahasa: klaim tak terverifikasi (R-04), superlatif yang tidak ada di daftar
  kata (R-07), testimoni (R-05), nada (R-10).
- **Keputusan desain 1 — Writer tidak menerima rulebook.** Ia hanya tahu fakta yang boleh
  dan yang dilarang. Penulis konten bukan pengawas kepatuhannya sendiri; kalau ia tahu
  seluruh aturan, ia akan menghindari kata tanpa memahami maksudnya, dan siklus
  tolak → perbaiki tidak akan pernah terjadi.
- **Keputusan desain 2 — setiap temuan lapis model wajib mengutip teks yang benar-benar
  ada di draf.** Kutipan yang tidak ditemukan dibuang otomatis, dan pembuangannya dicatat.
  Ini yang membuat model tidak bisa mengarang pelanggaran.
- **Keputusan desain 3 — gerbang approval di level eksekusi**, bukan instruksi prompt.
  Token `plan_id` sekali pakai; pemohon tidak boleh menyetujui aksinya sendiri.
- **Lapis distribusi — satu mesin, tiga permukaan.** `mcp_server/` mengekspos 19 tool
  stateless di atas `engine/` yang sama (transport stdio untuk WorkBuddy, HTTPS untuk
  klien jarak jauh); `web/` adalah BFF + frontend yang hanya menjangkau 5 tool dan
  sengaja **tidak memiliki** `approve_publication`; tiga skill WorkBuddy membawa batas
  peran ke percakapan. Tidak ada aturan yang ditulis ulang di lapisan mana pun —
  `engine/reviewer.py` tetap satu-satunya penilai. Server MCP live di Railway dengan
  token transport terpisah dari kunci approver manusia.

### 3c. Bagaimana prompt design menggerakkan perilaku

| Perilaku yang diinginkan | Teknik |
|---|---|
| Menolak dengan alasan yang bisa diperiksa | Format temuan wajib `rule_id` + `span` (kutipan persis) + `reason` + `fix`; validator membuang temuan tanpa kutipan |
| Tidak mengarang fakta | Planner hanya boleh mengambil isi dari bagian "Klaim yang BOLEH"; Writer dilarang menambah angka/bahan di luar rencana |
| Tidak menyinggung halal tanpa bukti | Aturan mutlak di prompt Writer: klaim halal hanya bila ada di fakta boleh **beserta nomornya** |
| Berhenti, tidak berputar | Batas 3 iterasi di orkestrator; putaran ke-3 yang masih gagal → ESKALASI ke manusia |
| Belajar nada, bukan menyalin fakta | Contoh dari `approved_posts.json` disisipkan sebagai rujukan nada, dengan peringatan eksplisit "tiru nadanya, jangan salin faktanya" |

## 4. Business Value

| Metrik | Sebelum | Sesudah | Sumber angka |
|---|---|---|---|
| Waktu memeriksa 1 draf | ±5–10 menit (manual, bergantung ingatan) | **< 1 detik** untuk lapis kode | 1100 eksekusi ≈ 60 detik, termasuk OCR C-17 (`docs/OFFICIAL_CASES_RUN.md`) |
| Aturan yang diperiksa konsisten | 3–5 yang diingat | **21 aturan** (R-01..R-21) + batas 3 platform | `dataset_c/rulebook_claims.md` |
| Klaim bermasalah yang tertangkap | ditemukan tidak sengaja | **8 temuan** pada draf agensi v1, 0 pada v2 | siklus uji WorkBuddy |
| Konsistensi hasil | berbeda antar orang | **1100 eksekusi, 0 penyimpangan** | 22 kasus × 50 ulangan |
| Jejak audit | tidak ada | rantai hash; tiap tolakan & persetujuan tercatat | `engine/governance.py` |

**Batas yang kami akui:** lapis model belum diuji dengan provider sungguhan — yang
terbukti baru jalurnya, bukan kualitas penilaiannya. Dan 4 dari 26 kasus (20 resmi +
6 cadangan) berstatus N/A karena kami memilih satu skenario. Keduanya ditulis terbuka di
`02_test_results.md`, bukan disembunyikan. Situs `web/` belum dideploy; yang live baru
MCP service.
