# Matriks Keputusan — Pilih Challenge (isi hari ini, 27 Okt)

> Deadline submission saat keputusan ini diambil: **1 November 2026** (kemudian diundur ke
> **7 November 2026**). Kunci pilihan malam ini agar punya 4 hari penuh untuk build.

## Perbandingan Singkat

| Aspek | A — Workplace Brain | B — Office Agent | C — Creator Agent |
|---|---|---|---|
| Inti build | Q&A + retrieval + kontrol izin | Dekomposisi + plan/approve + mock tools | Multi-agent (3+) + rulebook review |
| Kompleksitas teknis | Sedang (izin adalah kuncinya) | Sedang-tinggi (orkestrasi alur approval) | Tinggi (koordinasi 3 agent) |
| Pembeda paling dinilai juri | Penolakan yang "tidak mengisyaratkan" | Layar konfirmasi + audit log | Siklus tolak→perbaiki→setujui yang terlihat |
| Risiko gagal kritis | Bocor data RESTRICTED | Eksekusi tanpa approval | Klaim terlarang terpublikasi |
| Paling cocok jika tim… | suka logika izin & retrieval | suka workflow & UX approval | suka konten & aturan regulasi |
| Dataset tersedia | ✔ lengkap (20 kasus) | ✔ lengkap (20 kasus) | ✔ lengkap (20 kasus) |

## Pertanyaan Penentu (jawab jujur)

1. **Mana yang bisa didemokan paling meyakinkan dalam 8 menit?** Demo B paling visual (layar konfirmasi). Demo A paling "diam-diam meyakinkan" (penolakan). Demo C paling dramatis (siklus revisi).
2. **Mana yang paling tahan uji kejutan 90 detik?** A dan B punya aturan keras yang mudah diverifikasi juri (izin/approval). C tergantung kualitas rulebook-mu.
3. **Mana yang paling jarang dipilih peserta lain?** (Cek diskusi grup WA.) Memilih yang jarang bisa mengurangi persaingan langsung — tapi 9 finalis dinilai lintas-challenge dengan rubrik sama, jadi pilih yang bisa kamu kerjakan **paling baik**, bukan yang paling gampang.

## Rekomendasi Berbasis Dataset Ini

- **A** jika tim kecil (1–2 orang): fokus pada permission-check + sitasi; bonus PII masking dan freshness sudah terpetakan di kasus uji.
- **B** jika tim suka detail UX: mock tools + layar konfirmasi + audit log memberi bukti visual terbanyak untuk dimensi Responsible AI & UX.
- **C** jika tim nyaman membangun 3 workflow yang saling lempar: potensi skor AI Interaction & Innovation paling tinggi, tapi butuh disiplin log.

## Keputusan

```
Challenge terpilih : C — The Creator Agent
Skenario           : Peluncuran produk (product launch), kategori bodycare & beautycare
Alasan 1 baris     : Penilaian konten adalah pekerjaan yang bisa diperiksa objektif —
                     setiap tolakan punya nomor aturan, kutipan, dan bukti.
Diputuskan pada    : 2026-10-30 (dikunci; lihat catatan perubahan di bawah)
```

## Kenapa C, dan apa yang berubah dari rencana awal

Awalnya proyek ini dibangun untuk **Challenge A** (asisten kepatuhan halal internal:
status produk, dampak sertifikat kedaluwarsa, jawaban CS). Arah itu ditinggalkan karena
tiga alasan yang bisa dipertanggungjawabkan, bukan karena A lebih sulit:

1. **A dinilai dari ketiadaan.** Bukti terbaiknya adalah penolakan yang tidak
   mengisyaratkan — sulit ditunjukkan dalam 8 menit tanpa terlihat seperti error.
   C dinilai dari **siklus yang terlihat**: tolak → perbaiki → setujui.
2. **C memakai aset yang sudah ada.** Engine halal (R-03 terhadap registri sertifikat,
   pemeriksaan harga, audit log) bisa dipindahkan sebagai modul Reviewer. Tidak ada
   pekerjaan yang dibuang — lihat `dataset_halal/` dan `engine/halal_engine.py`.
3. **Handbook menyebut "klaim halal tanpa sertifikasi yang sah"** sebagai contoh masalah
   Challenge C. Domain halal tetap on-target, bukan menyimpang dari skenario.

Yang dibuang: dasbor pemantauan sertifikat dan copilot CS (konsep Challenge A).
Yang dipakai ulang: `governance.py` (audit hash-chain, gerbang approval), logika
pemeriksaan klaim, dan seluruh pemahaman domain halal.

**Konsekuensi yang diterima:** 4 dari 26 kasus (20 resmi + 6 cadangan) berstatus N/A
karena kita memilih satu skenario: C-15 multibahasa, C-18 suntingan manusia,
C-19 kit reseller, C-20 konten pembelajaran. Itu ditulis terbuka di
`02_test_results.md`, bukan disembunyikan. (Angka di paragraf ini diperbarui 6 Nov;
keputusan memilih Challenge C tidak berubah.)
