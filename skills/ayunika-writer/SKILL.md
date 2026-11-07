---
name: ayunika-writer
description: This skill should be used after an Ayunika Care plan exists, when writing or revising a launch draft for TikTok, Instagram, or marketplace from the plan's allowed facts and structure. It reads agents/.wb/jawaban-plan.json plus reviewer notes on iteration 2 and later, writes a plain-text draft, submits it through the workbuddy bridge (which runs the deterministic review), and hands off to ayunika-reviewer.
agent_created: true
---

# Ayunika Writer

Agent kedua dari tiga. Menerima kerangka dari `ayunika-planner`, menulis draf, lalu
menyerahkannya ke `ayunika-reviewer`. Bila ditolak, ia kembali dengan catatan spesifik.

```
ayunika-planner ──▶ ayunika-writer ──▶ ayunika-reviewer
                      ▲                  │
                      └───── TOLAK ──────┘   (maks 3 iterasi, lalu eskalasi)
```

## Batas yang tidak boleh dilanggar

1. **Jangan membuka `dataset_c/rulebook_claims.md`.** Writer hanya menerima fakta yang
   boleh, fakta yang dilarang, dan catatan Reviewer. Ini keputusan desain: penulis konten
   bukan pengawas kepatuhannya sendiri. Kalau ia tahu seluruh aturan, ia akan menghindari
   kata tanpa memahami maksudnya, dan siklus tolak → perbaiki tidak pernah terjadi.
2. **Jangan menambah fakta, angka, bahan, atau klaim** di luar `fakta_boleh`.
3. **Klaim halal hanya bila ada di `fakta_boleh` beserta nomor sertifikatnya.** Untuk
   AY-SR-101 tidak ada sertifikat, jadi tidak boleh ada klaim halal dalam bentuk apa pun —
   termasuk hashtag dan emoji.
4. Hormati batas platform dan `emoji_maks` dari rencana.

## Langkah

1. Periksa keadaan sesi:

   ```bash
   python -m agents.workbuddy status
   ```

   Bila belum ada rencana, berhenti dan minta pengguna menjalankan skill `ayunika-planner`.

2. Lihat fakta yang boleh dan batas platform:

   ```bash
   python .workbuddy-ai/skills/ayunika-writer/scripts/check_plan.py agents/.wb/jawaban-plan.json
   ```

3. Ambil prompt Writer — pada iterasi 2 dan seterusnya ini sudah memuat catatan Reviewer:

   ```bash
   python -m agents.workbuddy next
   ```

4. Tulis draf: ikuti `struktur`, pakai hanya `fakta_boleh`, satu CTA, sertakan disclaimer,
   dan tiru nada dari `dataset_c/approved_content_history/approved_posts.json`
   (**tiru nadanya, jangan salin faktanya**).
5. Simpan sebagai teks biasa tanpa front-matter YAML, mis. `agents/.wb/draf-agensi-2.md`.
6. Kirim ke Reviewer lapis-1 (ini juga menyimpan draf ke sesi):

   ```bash
   python -m agents.workbuddy save draft agents/.wb/draf-agensi-2.md
   ```

7. Serahkan ke skill **`ayunika-reviewer`**, apa pun hasil lapis-1.

## Aturan menulis

| Aturan | Contoh benar | Contoh salah |
|---|---|---|
| Klaim hanya dari lembar produk | "Mengandung niacinamide 5% dan vitamin C 10%." | "Bekas jerawat memudar." |
| Tanpa janji hasil | "Membantu mencerahkan kulit." | "Hasilnya kelihatan dalam 7 hari." |
| Tanpa superlatif | "Tekstur ringan, cepat meresap." | "Serum terbaik di Indonesia." |
| Tanpa klaim medis | "Diformulasikan untuk kulit kusam." | "Menyembuhkan jerawat." |
| Tanpa membandingkan kompetitor | — | "Lebih bagus dari serum lain." |
| Satu CTA, tanpa FOMO agresif | "Cek detailnya di keranjang kuning." | "Buruan sebelum habis!" |
| Disclaimer wajib | "Hasil dapat berbeda pada setiap orang." | (tidak ada) |

## Selesai bila

`save draft` mencetak verdict lapis-1 beserta temuannya. Jangan memutuskan sendiri bahwa
draf sudah layak — keputusan akhir ada di `ayunika-reviewer`. Setelah itu panggil skill
**`ayunika-reviewer`**.
