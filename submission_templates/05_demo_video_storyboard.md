# Storyboard Video Demo — Lolos (7:02)

> **Wajib ada:** gambaran proyek, kemampuan inti, refleksi build + tooling, dan minimal
> satu adegan agent **menolak / minta klarifikasi / menunggu approval**.
> Rekam 1080p, layar penuh, kursor besar, zoom 125–150%.
>
> **Sudah ada potongan jadi:** `video/Lolos_Demo.mp4` — **7:02**, 1920×1080, **30 scene**,
> dibangun dari keluaran nyata (`video/capture.py` → `video/build.py`). **Tanpa narasi
> suara**; caption terbakar.
>
> **Catatan timecode:** tabel di bawah adalah rencana potongan 6:30. Potongan final 7:02
> punya 30 scene, termasuk dua scene tambahan untuk C-17 (kartu produk + OCR). Untuk
> voice-over, pakai timecode aktual dari `video/build.py`, bukan tabel ini.

## Struktur Menit-per-Menit

| Menit | Segmen | Isi | Yang tampil di layar |
|---|---|---|---|
| 0:00–0:40 | Hook & judul | Nama + nilai + challenge & skenario | Slide judul: **Lolos** — "Reviewer konten peluncuran kosmetik" |
| 0:40–1:30 | Masalah nyata | Brief berisi 4 dari 5 pesan yang melanggar | `dataset_c/briefs/BRF-101...md` — sorot baris ❌ |
| 1:30–2:10 | Arsitektur | Diagram 40 detik, zoom ke siklus Writer ⇄ Reviewer | `diagram/architecture_challenge_c.png` |
| 2:10–3:20 | **Adegan A — menolak** | Draf agensi → 8 temuan, tiap temuan ada kutipan + aturan | Terminal: `save draft` menampilkan TOLAK |
| 3:20–4:20 | **Adegan B — siklus & approval** | Revisi → LOLOS → plan approval tercatat | Terminal `save findings` → TERBIT, lalu `governance.py tail` |
| 4:20–5:10 | Bukti uji | 22 kasus × 50 ulangan, plus 3 kegagalan yang diperbaiki | `run_official_cases.py` output + `shots/C-B2.png` |
| 5:10–6:00 | Refleksi build | Yang mudah, yang sulit, di mana WorkBuddy membantu | Bahan dari `06_product_sharing.md` |
| 6:00–6:30 | Penutup | Nilai bisnis + batas yang diakui + visi | Slide akhir |

## Adegan Wajib — direkam dari terminal sungguhan

**Adegan A (2:10–3:20) — agent menolak, bukan sekadar error.**

```bash
cd "C:/.Hackathon Project"
python -m agents.workbuddy reset
python -m agents.workbuddy start AY-SR-101 tiktok
python -m agents.workbuddy save plan agents/.wb/jawaban-plan.json
python -m agents.workbuddy save draft agents/.wb/draf-agensi-1.md
```

Yang harus terlihat di layar (jangan dipotong):

```
LAPIS-1 (kode)
AY-SR-101 · tiktok · iterasi 1 → TOLAK
  ✗ R-03 “Sudah halal, tinggal nunggu sertifikatnya keluar.”
      alasan: Klaim halal, tetapi produk belum punya sertifikat yang sah
      perbaiki: Hapus seluruh klaim halal sampai sertifikat terbit
  ✗ R-06 “Promo peluncuran Rp149.000 untuk 100 pembeli pertama.”
      alasan: Harga promo disebut Rp149.000, padahal promo resmi Rp129.000
  …
```

**Narasi:** *"Perhatikan bentuk penolakannya: bukan 'konten tidak valid', tapi nomor
aturan, kalimat yang bermasalah, dan apa yang harus ditulis. Itu bedanya alat kepatuhan
dengan penolak otomatis."*

Lalu lapis model (R-04 + R-10) — dua temuan yang **tidak mungkin** muncul dari kode:

```bash
python -m agents.workbuddy next                       # prompt lapis-2
python -m agents.workbuddy save findings agents/.wb/temuan-lapis2-1.json
```

**Adegan B (3:20–4:20) — siklus selesai dan approval manusia.**

```bash
python -m agents.workbuddy save draft agents/.wb/draf-agensi-2.md
python -m agents.workbuddy save findings agents/.wb/temuan-lapis2-2.json
cd engine; python governance.py tail 6
```

Yang harus terlihat: `LOLOS di iterasi 2 · terbit dengan plan PLAN-XXXXXXXX`, lalu baris
audit `plan_propose → plan_approve → execute`.

**Narasi:** *"Tidak ada yang terbit tanpa baris approval itu. Dan karena log-nya rantai
hash, kalau saya ubah satu kata di sini, seluruh rantai terdeteksi rusak."*

> Opsional 20 detik yang kuat: ubah satu baris `audit.jsonl`, jalankan
> `python governance.py verify` → `RUSAK: entri #N isinya diubah`. Kembalikan filenya.

## Adegan Pendukung (4:20–5:10) — kejujuran angka

```bash
python engine/run_official_cases.py --ulang 50
```

Tampilkan tiga angka dan **sebut bedanya**: `73/73` asersi mekanisme, `40/40` run loop,
`20/20 × 50` kasus resmi. Lalu buka `shots/C-B2.png` dan ceritakan:

**Narasi:** *"Kasus ini dulu lolos total. Kuota '5 kursi' tidak diperiksa karena kami
hanya membandingkan harga. Setelah diperbaiki, angka ketersediaan sekarang dibandingkan
dengan registri. Kami menaruhnya di video justru karena pernah gagal."*

## Checklist Sebelum Rekam

- [ ] `python -m agents.workbuddy reset` dulu supaya sesi bersih dan bisa diulang
- [ ] Terminal font ≥ 16pt, lebar jendela cukup (jangan ada teks terpotong)
- [ ] Tutup tab pribadi & notifikasi
- [ ] Rekam 1080p, 30fps; audio terpisah kalau bisa
- [ ] Durasi 6:00–6:45 (dalam rentang 5–8 menit)
- [ ] Ekspor `Lolos_Demo_[Tim].mp4`, upload unlisted, simpan link + file cadangan

## Naskah Pembuka (3 kalimat)

> "Tim marketing kosmetik menulis konten dari brief — dan brief itu sendiri sering berisi
> klaim yang melanggar aturan. Di dataset kami, 4 dari 5 pesan kunci di brief melanggar.
> Lolos adalah tiga agent yang menolak, menjelaskan alasannya, dan memperbaiki — sebelum
> konten itu pernah terbit."

## Yang Sebaiknya TIDAK Direkam

- Layar penuh kode yang di-scroll cepat (juri tidak bisa membaca)
- Klaim "akurat 100%" — kami tidak mengukurnya
- Demo lapis model seolah-olah hasilnya sudah teruji produksi. Sebut apa adanya:
  jalurnya terbukti, kualitas model belum diukur.
