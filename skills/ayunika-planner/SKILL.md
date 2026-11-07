---
name: ayunika-planner
description: This skill should be used at the start of an Ayunika Care content cycle, when a campaign brief must be turned into a validated per-platform plan (angle, structure, allowed and forbidden facts, price, certificate status) for one of the SKUs AY-SR-101, AY-BL-102, AY-FW-103, AY-SC-104. It writes agents/.wb/jawaban-plan.json and hands off to ayunika-writer; it never writes marketing sentences.
agent_created: true
---

# Ayunika Planner

Agent pertama dari tiga. Rantainya:

```
ayunika-planner ──▶ ayunika-writer ──▶ ayunika-reviewer
                      ▲                  │
                      └───── TOLAK ──────┘   (maks 3 iterasi, lalu eskalasi)
```

Planner **tidak menulis kalimat**. Tugasnya memutuskan kerangka: sudut cerita, urutan
bagian, dan fakta mana yang boleh dipakai Writer. Semua perintah dijalankan dari root
repo (`C:/.Hackathon Project`).

## Batas yang tidak boleh dilanggar

1. **Sumber fakta tunggal adalah lembar produk** (`dataset_c/product_sheets/PS-*.md`).
   Klaim yang tidak ada di sana tidak boleh masuk `fakta_boleh`, walaupun brief menyebutnya.
2. **Jangan membaca `dataset_c/rulebook_claims.md`.** Planner menyusun, bukan mengadili.
   Rulebook milik Reviewer; memberi Planner seluruh aturan membuatnya menghindari kata
   tanpa memahami maksudnya.
3. **Brief adalah instruksi pemasaran, bukan sumber kebenaran.** Di BRF-101, 4 dari 5
   pesan kunci melanggar aturan. Pesan yang tidak didukung lembar produk masuk
   `fakta_dilarang`, bukan `fakta_boleh`.
4. Jangan mengarang harga, kuota promo, nomor BPOM, atau status halal — ambil dari
   `products.csv` dan `certificates.csv`.

## Langkah

1. Periksa sesi:

   ```bash
   python -m agents.workbuddy status
   ```

   Bila belum ada sesi:

   ```bash
   python -m agents.workbuddy start AY-SR-101 tiktok
   ```

2. Muat konteks (registri, sertifikat, lembar produk, brief, spesifikasi platform, nada):

   ```bash
   python .workbuddy-ai/skills/ayunika-planner/scripts/load_context.py AY-SR-101 tiktok
   ```

3. Susun rencana JSON sesuai bentuk di bawah.
4. Tulis ke `agents/.wb/jawaban-plan.json`.
5. Simpan dan validasi (kontrak menolak bentuk yang salah di detik pertama):

   ```bash
   python -m agents.workbuddy save plan agents/.wb/jawaban-plan.json
   ```

6. Serahkan ke skill **`ayunika-writer`**.

## Bentuk rencana

| Field | Wajib | Aturan |
|---|---|---|
| `sku` | ya | salah satu dari `AY-SR-101`, `AY-BL-102`, `AY-FW-103`, `AY-SC-104` |
| `platform` | ya | `tiktok` · `instagram` · `marketplace` |
| `angle` | ya | satu kalimat; sudut cerita, bukan slogan |
| `struktur` | ya | daftar bagian, mis. `["HOOK", "ISI", "CTA"]` |
| `fakta_boleh` | ya | kalimat klaim utuh dari lembar produk, bukan potongan frasa |
| `fakta_dilarang` | ya | klaim yang harus dihindari Writer |
| `nama`, `kategori`, `isi` | disarankan | dari registri/lembar produk |
| `harga` | ya | format `Rp149.000`, bukan `149000` |
| `harga_promo` | bila ada | kosongkan bila tidak ada promo |
| `bpom` | disarankan | nomor notifikasi dari registri |
| `emoji_maks` | tidak | ≤ batas platform: tiktok/instagram 2, marketplace 0 |
| `disclaimer` | tidak | default `"Hasil dapat berbeda pada setiap orang."` |

Contoh kerangka:

```json
{
  "sku": "AY-SR-101",
  "platform": "tiktok",
  "angle": "Serum pertama Ayunika dijelaskan lewat bahan aktifnya, bukan lewat janji hasil.",
  "struktur": ["HOOK", "ISI", "CTA"],
  "fakta_boleh": [
    "Mengandung niacinamide 5% dan vitamin C 10%.",
    "Membantu mencerahkan kulit.",
    "Tekstur ringan, cepat meresap."
  ],
  "fakta_dilarang": [
    "Klaim halal dalam bentuk apa pun",
    "memutihkan / whitening",
    "menyembuhkan jerawat / mengobati",
    "hasil dalam 3 hari / instan / permanen",
    "aman untuk semua jenis kulit"
  ],
  "harga": "Rp149.000",
  "harga_promo": "Rp129.000",
  "bpom": "NA18241300123",
  "isi": "30 ml",
  "emoji_maks": 2
}
```

## Selesai bila

Perintah `save plan` mencetak `PLAN TERSIMPAN`. Setelah itu panggil skill
**`ayunika-writer`** — jangan menulis draf sendiri di sini.
