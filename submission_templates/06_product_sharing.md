# Product Sharing — Nilai Tambah WorkBuddy

> 250–400 kata. Fitur yang **benar-benar dipakai**, bukan daftar kemampuan produk.

## 1. Di Mana WorkBuddy Menghemat Waktu

| Fitur WorkBuddy | Untuk apa di proyek ini | Perkiraan hemat |
|---|---|---|
| Agent dengan akses file + terminal | Menulis `reviewer.py`, `pipeline.py`, `layer2.py`; menjalankan 1100 eksekusi uji; memperbaiki bug dari traceback | ±10–12 jam vs menulis lalu menguji manual di dua alat terpisah |
| Web search & fetch | Membaca **teks resmi** PerBPJPH 2/2026 dan 3/2026 dari JDIH BPK — bukan ringkasan sekunder | ±3 jam; dan mencegah kami mengutip pasal dari ingatan |
| Inspeksi gambar | Memeriksa hasil render diagram dan 25 kartu bukti (`ViewImage`), menemukan teks terpotong | ±1–2 jam |
| Percakapan iteratif | Mempertajam rulebook lewat temuan uji: R-01 `\bsembuh\b` tidak menangkap "SEMBUHKAN" | tidak terhitung — ini yang paling berpengaruh |

Tanpa poin terakhir, proyek ini akan berhenti di "21 aturan terlihat rapi di dokumen".
Yang membuatnya bekerja adalah siklus: jalankan → lihat yang lolos padahal melanggar →
perbaiki.

## 2. Wawasan Utama

- **Gerbang harus di level eksekusi, bukan prompt.** Kami sempat mengandalkan instruksi
  "jangan publikasikan tanpa approval". Setelah diuji, gerbangnya dipindah ke kode:
  `execute()` menolak plan yang belum APPROVED, token sekali pakai, pemohon tidak boleh
  menyetujui aksinya sendiri. Prompt bisa dilupakan model; kode tidak.
- **Model tidak boleh jadi hakim tunggal.** Reviewer lapis-2 bisa mengarang pelanggaran,
  jadi setiap temuan wajib membawa kutipan yang benar-benar ada di draf. Kutipan palsu
  dibuang — dan pembuangannya **dicatat**, bukan dihilangkan.
- **Log adalah fitur, bukan pelengkap.** Audit chain menyelamatkan kami saat melacak
  mengapa satu kasus berubah hasil, dan ternyata jadi bukti terkuat di video demo.

## 3. Pelajaran

- **Mulai dari kasus uji, bukan dari fitur.** 20 kasus resmi memaksa desain jadi tajam;
  tanpa itu kami akan membangun dasbor yang cantik dan tidak menjawab apa pun.
- **Data yang punya jebakan lebih berguna daripada data rapi.** Brief yang 4 dari 5
  pesannya melanggar mengajarkan lebih banyak daripada 20 contoh yang sempurna.
- **Batas 3 iterasi menyelamatkan kami** dari loop tak berujung — dan justru jadi salah
  satu hal yang paling mudah didemokan.

## 4. Kritik Membangun

WorkBuddy belum menerbitkan API key, sehingga agent yang berjalan di dalamnya tidak bisa
dipanggil dari backend website. Kami mengakalinya dengan jembatan berkas
(`agents/workbuddy.py`): skrip mencetak prompt, model WorkBuddy menjawab, jawabannya
disimpan, lalu Reviewer menilai. Jalur ini bekerja dan sudah diuji, tapi setiap langkah
butuh satu balasan manual — cukup untuk demo, tidak untuk 100 konten/hari. Yang kami
harapkan: cara resmi memanggil model WorkBuddy secara programatik.
