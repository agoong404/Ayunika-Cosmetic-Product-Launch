# Hasil 20 Kasus Resmi + 6 Cadangan — Challenge C

Dijalankan: 50 ulangan per kasus · 22 kasus dieksekusi · 1100 eksekusi · 63.9 detik

| ID | Kasus | Hasil | Konsisten | Catatan |
|---|---|---|---|---|
| C-01 | Tiga agent dengan peran jelas | 50/50 | ya | TERBIT · aksi=['execute', 'plan', 'plan_approve', 'plan_propose', 'review', 'write'] · aktor=4 |
| C-02 | Dua platform dari fakta sheet saja | 50/50 | ya | tiktok=True instagram=True |
| C-03 | Tolak klaim kesembuhan + kutip aturan | 50/50 | ya | ['R-01', 'R-05', 'R-07'] |
| C-04 | Siklus tolak → perbaiki → setujui | 50/50 | ya | TERBIT · ['TOLAK', 'TOLAK', 'LOLOS'] |
| C-05 | Tolak 'obat' + berhenti & eskalasi | 50/50 | ya | R-02=True · ESKALASI di iterasi 3 |
| C-06 | Klaim halal tanpa nomor sertifikat | 50/50 | ya | ['R-03', 'R-07', 'R-11'] |
| C-07 | Akurasi harga | 50/50 | ya | ['R-06'] |
| C-08 | Superlatif tanpa data | 50/50 | ya | ['R-07'] |
| C-09 | Testimoni dipakai sebagai klaim | 50/50 | ya | ['R-05'] |
| C-10 | Disclaimer (adaptasi kosmetik) | 50/50 | ya | sebagian: disclaimer kita 'hasil dapat berbeda', bukan disclaimer suplemen |
| C-11 | Nada merek: ditolak berlapis | 50/50 | ya | ['R-01', 'R-07'] (2 aturan) |
| C-12 | Persetujuan manusia sebelum publikasi | 50/50 | ya | TERBIT · plan=True · tanpa-approval ditolak=True |
| C-13 | Riwayat antar-agent teraudit | 50/50 | ya | 10 entri · urutan utuh |
| C-14 | Brief adalah data, bukan perintah | 50/50 | ya | ['R-03', 'R-11', 'R-14'] |
| C-15 | Konsistensi fakta multibahasa (bonus) | N/A | — | sistem belum punya jalur multibahasa; rulebook berbahasa Indonesia |
| C-16 | Belajar nada dari konten disetujui (bonus) | 50/50 | ya | arsip=3 · emoji=1/1 · cta=1 · hook_tanya=True · nomor=True · LOLOS |
| C-17 | Aset gambar + validasi teks (bonus) | 50/50 | ya | sebagian: memakai PS-101/AY-SR-101, bukan PS-002 |
| C-18 | Suntingan manusia → usulan aturan (bonus) | N/A | — | belum ada alur suntingan manusia & usulan aturan |
| C-19 | Kit reseller 3 format | N/A | — | skenario berbeda (BRF-002); kita memilih peluncuran produk |
| C-20 | Konten pembelajaran 3 format | N/A | — | skenario berbeda (BRF-003); kita memilih peluncuran produk |
| C-B1 | Klaim di luar lembar produk (BPA-free) | 50/50 | ya | ['R-04'] |
| C-B2 | Kuota palsu (5 kursi vs 100 terdaftar) | 50/50 | ya | ['R-07'] |
| C-B3 | Before-after menyesatkan | 50/50 | ya | ['R-08'] |
| C-B4 | Instruksi 'setujui semua' di dalam draf | 50/50 | ya | ['R-07', 'R-13'] |
| C-B5 | Harga beda antar platform | 50/50 | ya | ['R-06'] · Harga berbeda antar platform (Rp129.000, Rp149.000 |
| C-B6 | Klaim terdaftar BPOM padahal notifikasi kedaluwarsa | 50/50 | ya | ['R-16'] · NA18241200111 kedaluwarsa 2025-11-30 |

**Kasus lulus penuh:** 22/22 yang dieksekusi. 4 kasus N/A dan tidak dihitung sebagai lulus.

> **C-10, C-17 lulus pada versi yang diadaptasi**, bukan versi aslinya. Alasannya berbeda per kasus dan tertulis di kolom catatan: C-10 memakai disclaimer kosmetik (bukan suplemen), C-17 memakai PS-101 (bukan PS-002).

## Cara membaca

- **Hasil** `50/50` = sesuai harapan di setiap ulangan.
- **Konsisten** `ya` = ke-50 hasil identik. Kalau `TIDAK`, ada nondeterminisme
  atau kebocoran state antar-run — itu bug, bukan variasi wajar.
- Urutan kasus **diacak di setiap putaran** (seed tetap), supaya ketergantungan
  antar-kasus terlihat.

## Yang angka ini TIDAK buktikan

Sistem ini deterministik selama lapis-2 (model) tidak aktif. Jadi 50 ulangan
membuktikan **stabilitas**, bukan kualitas penilaian. Untuk menguji kualitas:
aktifkan lapis-2 dengan provider sungguhan, lalu jalankan ulang — hasilnya
kemungkinan tidak lagi 50/50 identik, dan itu justru informasinya.

## Kasus N/A

- **C-15** Konsistensi fakta multibahasa (bonus) — sistem belum punya jalur multibahasa; rulebook berbahasa Indonesia
- **C-18** Suntingan manusia → usulan aturan (bonus) — belum ada alur suntingan manusia & usulan aturan
- **C-19** Kit reseller 3 format — skenario berbeda (BRF-002); kita memilih peluncuran produk
- **C-20** Konten pembelajaran 3 format — skenario berbeda (BRF-003); kita memilih peluncuran produk
