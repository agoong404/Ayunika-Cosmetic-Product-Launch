# Mulai dari Sini — mengaktifkan skill & mencoba sendiri

> Semua perintah dijalankan dari root repo: `C:/.Hackathon Project`
> Tidak butuh API key. Tidak butuh `pip install` — seluruh kode memakai stdlib.
> Satu pengecualian: kasus **C-17** (aset gambar) membutuhkan binary **Tesseract**,
> bukan paket Python.
>
> **Shell:** perintah di sini ditulis agar jalan di **PowerShell maupun Git Bash**.
> Jangan memakai `&&` (itu khusus bash) — di PowerShell pakai `;` atau pisahkan baris.

---

## 1. Mengaktifkan tiga skill

Skill ada di `.workbuddy-ai/skills/` (project-level), bukan di folder WorkBuddy:

```
.workbuddy-ai/skills/
├── ayunika-planner/SKILL.md
├── ayunika-writer/SKILL.md
└── ayunika-reviewer/SKILL.md
```

**Langkah:**

1. Tutup WorkBuddy, buka lagi, lalu buka percakapan baru **di workspace ini**.
   Skill dibaca saat sesi dimulai — sesi yang sedang berjalan tidak memuatnya.
2. Tanyakan di chat: *"skill apa saja yang tersedia?"*
   Yang harus muncul: `ayunika-planner`, `ayunika-writer`, `ayunika-reviewer`.
3. Panggil dengan namanya, misalnya:
   *"pakai skill ayunika-planner untuk AY-SR-101 di tiktok"*

**Kalau tidak muncul**, salin ke level user lalu restart sekali lagi:

PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME/.workbuddy-ai/skills" | Out-Null
Copy-Item -Recurse .workbuddy-ai/skills/ayunika-planner,
  .workbuddy-ai/skills/ayunika-writer,
  .workbuddy-ai/skills/ayunika-reviewer "$HOME/.workbuddy-ai/skills/"
```

Git Bash:

```bash
mkdir -p ~/.workbuddy-ai/skills
cp -r .workbuddy-ai/skills/ayunika-planner \
      .workbuddy-ai/skills/ayunika-writer \
      .workbuddy-ai/skills/ayunika-reviewer ~/.workbuddy-ai/skills/
```

> Skill hanya mengatur **cara berpikir** agent (peran, batas, urutan). Perintah yang
> dijalankannya tetap perintah biasa di bawah ini — jadi kamu bisa mengerjakan semuanya
> tanpa skill, dan hasilnya sama.

---

## 2. Uji cepat sebelum mulai (2 menit)

```bash
cd "C:/.Hackathon Project"
python -m agents.workbuddy status
cd engine
python run_reviewer_tests.py
```

Harapan: `73/73 lulus`. Kalau ini gagal, jangan lanjut — ada yang salah di lingkungan.

Untuk kasus **C-17** (kartu produk + OCR), pasang Tesseract sekali:

```
winget install --id UB-Mannheim.TesseractOCR -e
```

Kalau `A-01` gagal, berarti binary itu belum ada — bukan bug kode.

---

## 3. Siklus penuh, langkah demi langkah

Jalankan satu per satu. Jangan lompat: tiap perintah mengubah state sesi.

| # | Perintah | Yang harus muncul |
|---|---|---|
| 1 | `python -m agents.workbuddy reset` | `Sesi dihapus. Audit log TIDAK dihapus — itu append-only.` |
| 2 | `python -m agents.workbuddy start AY-SR-101 tiktok` | `Sesi dibuat: AY-SR-101 / tiktok` + prompt Planner |
| 3 | `python -m agents.workbuddy save plan agents/.wb/jawaban-plan.json` | `Rencana diterima · 4 fakta boleh · 7 fakta dilarang` |
| 4 | `python -m agents.workbuddy next` | `PROMPT SISTEM` + prompt Writer |
| 5 | `python -m agents.workbuddy save draft agents/.wb/draf-agensi-1.md` | `LAPIS-1 (kode)` → `TOLAK` → `12 pemeriksaan · 6 temuan` |
| 6 | `python -m agents.workbuddy next` | prompt **lapis-2** (draf + lembar produk + nada) |
| 7 | `python -m agents.workbuddy save findings agents/.wb/temuan-lapis2-1.json` | `2 temuan mentah · 2 diterima` → `13 pemeriksaan · 8 temuan` → `TOLAK` |
| 8 | `python -m agents.workbuddy save draft agents/.wb/draf-agensi-2.md` | `iterasi 2 → LOLOS` · `12 pemeriksaan · 0 temuan` |
| 9 | `python -m agents.workbuddy save findings agents/.wb/temuan-lapis2-2.json` | `LOLOS di iterasi 2 · terbit dengan plan PLAN-XXXXXXXX` |
| 10 | `python -m agents.workbuddy status` | `TERBIT · iterasi 2/3` |
| 11 | `cd engine; python governance.py tail 6` | `plan_propose` → `plan_approve` → `execute` |
| 12 | `python governance.py verify` | `UTUH: rantai utuh (N entri)` |

**Yang perlu diperhatikan di langkah 5 dan 7:** jumlah temuannya berbeda.
Lapis kode menemukan **6**; setelah temuan model digabung menjadi **8**. Dua tambahan itu —
`R-04 "bekas jerawat memudar"` dan `R-10 "Buruan sebelum habis"` — tidak mungkin muncul
dari daftar kata.

> `plan_id` berubah setiap kali dijalankan. Itu wajar: setiap penerbitan punya token sendiri.

---

## 4. Coba sendiri (lab)

Buat berkas uji, lalu nilai. Hasil di bawah **sudah diverifikasi**.

```bash
# tulis draf uji (satu kalimat cukup)
python -c "open('.uji.md','w',encoding='utf-8').write('Serum ini dijamin memutihkan dalam 3 hari.')"

python .workbuddy-ai/skills/ayunika-reviewer/scripts/review.py .uji.md AY-SR-101 tiktok
```

| Kalimat | SKU | Hasil yang benar |
|---|---|---|
| `Serum ini dijamin memutihkan dalam 3 hari.` | AY-SR-101 | `TOLAK` · R-07, R-13 |
| `Produk ini sudah terdaftar BPOM.` | AY-SR-101 | `LOLOS` — notifikasi masih berlaku |
| `Produk ini sudah terdaftar BPOM.` | AY-SC-104 | `TOLAK` · **R-16** — notifikasi kedaluwarsa 2025-11-30 |
| `Bahan organik pilihan untuk kulit.` | AY-SR-101 | `TOLAK` · **R-18** — tidak ada sertifikat organik |
| `Produk ini bebas paraben.` | AY-SR-101 | `LOLOS` — memang tanpa paraben |
| `Produk ini bebas paraben.` | AY-BL-102 | `TOLAK` · **R-21** — komposisi memuat paraben |
| `Formula ini membunuh kuman 100%.` | AY-SR-101 | `TOLAK` · R-11, **R-20** |
| kalimat bersih, SKU `AY-XX-999` | — | `PERLU_DATA` (exit 3) — data produk tidak ada |

Bersihkan setelah selesai: `python -c "import os; os.remove('.uji.md')"`

### Audit kemasan (layer reviewer awal)

```bash
cd engine; python audit_kemasan.py --semua
```

Harapan: tiga produk `BERSIH`, dan **AY-SC-104 punya 3 masalah** (R-16, R-17, R-03).
Itu sengaja — satu SKU "bermasalah" membuat setiap aturan punya kasus uji.

### Kasus resmi (opsional, ±9 detik)

```bash
cd engine; python run_official_cases.py --ulang 50
```

Harapan: `utama 16/16`, `cadangan 6/6`, **1100 eksekusi**, `rantai audit UTUH`.

---

## 5. Kalau ada yang tidak jalan

| Gejala | Sebab | Perbaikan |
|---|---|---|
| `No module named agents` | salah direktori | `cd "C:/.Hackathon Project"` |
| `python` tidak dikenal | PATH | coba `py -m agents.workbuddy ...` |
| Skill tidak muncul di chat | sesi lama | restart WorkBuddy, buka chat baru; kalau tetap, salin ke `~/.workbuddy-ai/skills/` |
| `KeyError: SKU ...` | kode lama | pastikan `reviewer.py` memuat `dikenal = sku in self.products` |
| `save draft` bilang "belum ada rencana" | urutan terlewat | ulangi dari langkah 2–3 |
| `save findings` bilang "tahap bukan findings" | draf belum dikirim | jalankan langkah 5 dulu |
| Audit bertambah terus | memang append-only | `reset` hanya menghapus sesi, bukan log |

---

## 6. Mengubah data, bukan kode

Semua aturan membaca CSV. Untuk mencoba skenario baru, cukup edit:

| Berkas | Untuk mengubah |
|---|---|
| `dataset_c/products.csv` | harga, isi, nomor BPOM per SKU |
| `dataset_c/izin_edar.csv` | status notifikasi (R-16) |
| `dataset_c/izin_produksi.csv` | izin produksi per kategori (R-17) |
| `dataset_c/sertifikat_klaim.csv` | organik / uji dermatologis (R-18, R-19) |
| `dataset_c/komposisi_produk.csv` | komposisi INCI per SKU |
| `dataset_c/batas_pengawet.csv` | batas kadar pengawet (R-21) |
| `dataset_c/rulebook_claims.md` | aturan R-01..R-21 |

Setelah mengubah, jalankan ulang `python run_reviewer_tests.py` — kalau ada asersi yang
gagal, artinya perubahanmu mengubah perilaku yang sudah dijanjikan.
