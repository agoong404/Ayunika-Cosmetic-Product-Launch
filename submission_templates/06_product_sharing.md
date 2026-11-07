# Product Sharing — Nilai Tambah WorkBuddy

> 250–400 kata. Fitur yang **benar-benar dipakai**, bukan daftar kemampuan produk.

## 1. Di Mana WorkBuddy Menghemat Waktu

| Fitur WorkBuddy | Untuk apa di proyek ini | Perkiraan hemat |
|---|---|---|
| Agent dengan akses file + terminal | Menulis `reviewer.py`, `pipeline.py`, `layer2.py`; menjalankan 1100 eksekusi uji; memperbaiki bug dari traceback | ±10–12 jam vs menulis lalu menguji manual di dua alat terpisah |
| Web search & fetch | Membaca **teks resmi** PerBPJPH 2/2026 dan 3/2026 dari JDIH BPK — bukan ringkasan sekunder | ±3 jam; dan mencegah kami mengutip pasal dari ingatan |
| Inspeksi gambar | Memeriksa hasil render diagram dan 27 gambar bukti (`ViewImage`), menemukan teks terpotong | ±1–2 jam |
| MCP tool dari dalam percakapan | Memanggil 19 tool `mcp__lolos__*` (`list_products`, `run_cycle`, `review_draft`, `audit_verify`) tanpa meninggalkan WorkBuddy; engine yang sama, tanpa menyalin aturan | ±2–3 jam vs menulis klien HTTP sendiri |
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

WorkBuddy belum menerbitkan API key, sehingga model yang berjalan di dalamnya tidak bisa
dipanggil dari backend website. Kami mengakalinya dua kali. **Pertama**, jembatan berkas
(`agents/workbuddy.py`): skrip mencetak prompt, model menjawab, jawabannya disimpan, lalu
Reviewer menilai — bekerja dan teruji, tapi tiap langkah butuh satu balasan manual.
**Kedua**, yang akhirnya dipakai produksi: `mcp_server/` membalik arahnya. Alih-alih
memanggil model WorkBuddy dari luar, kami mengekspos mesin Ayunika Care sebagai 19 tool MCP
yang justru **dipanggil oleh** WorkBuddy lewat `~/.workbuddy-ai/mcp.json`. Tool bersifat
stateless, jadi tidak ada `session.json` yang diperebutkan dua klien. Situs publik `web/`
memakai jalur yang sama lewat BFF, dan `engine/reviewer.py` tetap satu-satunya penilai.

Yang masih kami harapkan: cara resmi memanggil model WorkBuddy secara programatik untuk
lapis-2. Karena itu belum ada, situs publik sengaja berjalan **tanpa LLM** — ia hanya
menilai 15 aturan deterministik, dan enam aturan yang butuh pemahaman bahasa dijalankan di
alur WorkBuddy. Kami menuliskan batas itu di halaman, bukan menyamarkannya.

**Expert yang dapat dipasang (ditambahkan 6 Nov, setelah video dibekukan).**
`expert/ayunika-compliance-team/` — **Ayunika Compliance Team**, empat agent: Rani
(lead), Bima (perencana), Citra (penulis), Dimas (penelaah). Setiap platform
(TikTok, Instagram, marketplace) mendapat satu rencana, satu naskah, dan satu
verdict; setiap penolakan menyebut nomor aturan dan mengutip kalimatnya; draf
yang ditolak diperbaiki sampai lolos, maksimal 3 iterasi lalu eskalasi. Rantai
berhenti di `request_approval` → `PROPOSED`, dan `approve_publication` tidak
pernah dipanggil.

Tim ini disusun untuk **brief yang berbunyi "build a team of AI agents"**:
tiap anggota adalah konteks terpisah, sehingga Writer tidak pernah melihat
rulebook yang hanya boleh dibaca Reviewer. Semua eksekusi lewat MCP service
yang sama (19 tool), jadi tidak ada aturan yang ditulis ulang di lapisan mana
pun — `engine/reviewer.py` tetap satu-satunya penilai.

Kami **tidak** menyalin `skills/` ke dalam paket: batas peran tiap anggota
sudah tertulis di agent MD-nya, dan menyalin `SKILL.md` lagi hanya
menciptakan sumber kebenaran kelima yang bisa menyimpang. `skills/` tetap ada
di repo sebagai jalur pemakaian mandiri.

Validasi resmi lolos tanpa peringatan; paket terdaftar di `my-experts` secara
**lokal**. Kami tidak mengklaim tautan bagikan publik: `sharecode` diterbitkan
server saat pengajuan Marketplace disetujui, dan itu belum kami lakukan.
Expert ini tidak muncul di video 7:02 — dibangun setelahnya, dan kami katakan
terus terang.

**Tiga kapabilitas bonus (juga 6 Nov, setelah video).** Lembar fakta ID/EN/Mandarin
dari satu kamus kanonik (`engine/multilingual.py`), kartu gambar yang dibaca ulang
lewat OCR, dan usulan aturan dari suntingan manusia yang berhenti di gerbang
approval — semuanya kini bisa dipanggil sebagai tool MCP. Ini yang membuat
expert di atas bisa menjawab keempat kriteria bonus yang sebelumnya berstatus N/A.
Bukti diuji **terpisah** (`engine/run_bonus_tests.py`, 32/32) supaya angka 1100
eksekusi / 22 kasus di video tidak berubah. Kamus fakta bukan mesin penerjemah,
kartu hanya untuk satu SKU, dan usulan yang disetujui tidak pernah aktif otomatis;
ketiga batas itu ditulis terbuka di `01_accountability_sheet.md`.
