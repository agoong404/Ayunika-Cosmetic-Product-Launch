---
name: lolos-reviewer
description: This skill should be used after a draft has been submitted, when judging it against the Lolos rulebook R-01..R-21 with two layers: deterministic code findings plus model judgment limited to R-04, R-05, R-07, R-08, R-10 and R-12. It requires exact quotes from the draft, records findings through the workbuddy bridge, returns a final verdict, and on TOLAK hands back to lolos-writer while on LOLOS it stops at the human approval gate.
agent_created: true
---

# Lolos Reviewer

Agent ketiga. Menilai draf dengan **dua lapis**, lalu memutuskan `TOLAK` atau `LOLOS`.
Ia satu-satunya agent yang membaca rulebook.

```
lolos-planner ──▶ lolos-writer ──▶ lolos-reviewer
                      ▲                  │
                      └───── TOLAK ──────┘   (maks 3 iterasi, lalu eskalasi)
```

## Dua lapis, dan siapa memeriksa apa

| Lapis | Dijalankan oleh | Memeriksa |
|---|---|---|
| 1 — kode | otomatis saat `save draft` | R-01, R-02, R-03, R-06, R-09, R-11, R-13, R-14, R-15: harga/angka/kuota, klaim halal vs registri, frasa terlarang, disclaimer, emoji, batas platform |
| 2 — model | langkah `save findings` di skill ini | hanya **R-04, R-05, R-07, R-08, R-10, R-12**: klaim tak terverifikasi, testimoni, superlatif di luar daftar kata, before-after, nada, kompetitor |

Temuan di luar enam aturan lapis-2 **ditolak** — bukan karena salah, tapi karena kode
sudah menanganinya dan pengulangan membuat laporan ganda.

## Aturan kutipan (tidak bisa ditawar)

Setiap temuan lapis-2 **wajib** membawa `span` yang disalin **persis** dari draf,
karakter demi karakter. Penjaga di `Reviewer.apply_llm_findings()` membuang temuan yang
kutipannya tidak ditemukan, dan **mencatat pembuangannya** (`dibuang_llm`). Model tidak
boleh mengarang pelanggaran; kalau mengarang, temuannya hilang dari laporan.

Nol temuan adalah jawaban yang sah. Model yang selalu menemukan pelanggaran sama tidak
bergunanya dengan model yang tidak menemukan apa pun.

## Langkah

1. Pastikan draf sudah masuk sesi:

   ```bash
   python -m agents.workbuddy status
   ```

   Tahap harus `findings`. Bila belum, minta pengguna menjalankan `lolos-writer` dulu.

2. Ambil prompt lapis-2 (draf + lembar produk + nada merek):

   ```bash
   python -m agents.workbuddy next
   ```

3. Baca draf dan rulebook `dataset_c/rulebook_claims.md`. Nilai hanya pada enam aturan
   lapis-2 di atas.
4. Susun temuan:

   ```json
   {"findings": [
     {"rule_id": "R-04",
      "span": "<salinan PERSIS satu kalimat dari draf>",
      "reason": "klaim tidak ada di lembar produk",
      "fix": "hapus klaim; tulis klaim yang ada di lembar produk"}
   ]}
   ```

5. Simpan, mis. `agents/.wb/temuan-lapis2-1.json`.
6. Hitung verdict final (penjaga menyaring kutipan palsu, lalu lapis-1 + lapis-2 digabung):

   ```bash
   python -m agents.workbuddy save findings agents/.wb/temuan-lapis2-1.json
   ```

7. Bertindak sesuai verdict:
   - **TOLAK** → serahkan kembali ke **`lolos-writer`** dengan catatan yang tercetak
     (iterasi berikutnya). Jangan memperbaiki draf sendiri di sini.
   - **LOLOS** → berhenti di **gerbang persetujuan manusia**. Jangan menerbitkan apa pun;
     publikasi hanya setelah manusia menyetujui `plan_id`.

## Pemeriksaan cepat di luar sesi

Untuk menilai draf apa pun tanpa mengubah sesi (tidak menulis audit kecuali `--log`):

```bash
# lapis-1 saja
python .workbuddy-ai/skills/lolos-reviewer/scripts/review.py draf.md AY-SR-101 tiktok

# lapis-1 + lapis-2 dengan berkas temuan
python .workbuddy-ai/skills/lolos-reviewer/scripts/review.py draf.md AY-SR-101 tiktok \
  --findings agents/.wb/temuan-lapis2-1.json
```

Keluaran berupa JSON `{verdict, jumlah_temuan, temuan[], dibuang_llm[]}`; kode keluar
`0` untuk LOLOS, `1` untuk TOLAK.

## Selesai bila

Verdict final tercetak dan tercatat di audit log. Setelah `LOLOS`, langkah berikutnya
adalah persetujuan manusia — bukan publikasi otomatis.

## SKU yang tidak ada di registri

Jangan berhenti dan jangan menganggapnya lolos. `Reviewer.review()` menangani ini:

| Kondisi | Verdict | Yang terjadi |
|---|---|---|
| Teks bersih, SKU tak dikenal | **`PERLU_DATA`** | Pemeriksaan teks jalan; harga/BPOM/halal/izin tidak dapat diverifikasi, dan itu dicatat |
| Ada pelanggaran teks, SKU tak dikenal | **`TOLAK`** | Pelanggaran yang bisa diperiksa tetap dilaporkan |

`PERLU_DATA` bukan lulus. Artinya: "saya tidak menemukan pelanggaran, tetapi saya juga
tidak punya data untuk menyatakan aman." Sampaikan itu apa adanya ke pengguna.
