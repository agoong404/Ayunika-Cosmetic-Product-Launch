# Dataset Challenge C — Product Launch (Bodycare & Beautycare)

> **DATA MOCK.** PT Ayunika Beauty Nusantara adalah perusahaan fiktif. Nomor BPOM dan
> nomor sertifikat halal di sini **fiktif** — jangan diverifikasi ke SIHALAL.
> Pola, kategori, dan format nomor mengikuti data nyata dari registri publik BPJPH.

**Skenario:** peluncuran produk · **Hero product:** Ayunika Bright Serum (AY-SR-101)
**Platform:** TikTok + Instagram + marketplace · **Tanggal simulasi:** 30 Okt 2026

---

## 1. Kenapa domain ini

Kosmetik adalah kategori dengan **dua rezim aturan yang bertumpuk**:

| Rezim | Mengatur | Konsekuensi bila salah |
|---|---|---|
| **BPOM** (klaim kosmetik) | Klaim manfaat, larangan klaim terapeutik, notifikasi | Produk ditarik, izin edar dicabut |
| **BPJPH** (jaminan halal) | Klaim halal, sertifikat, cakupan | Klaim palsu = pelanggaran konsumen |

Dan ada satu jebakan yang jarang disadari tim:

> **Kewajiban sertifikasi halal kosmetik baru berlaku 17 Oktober 2028** (PP 40/2026,
> penyesuaian atas PP 42/2024). Artinya kosmetik tanpa sertifikat **belum melanggar
> kewajiban** — tetapi **mengklaim halal tanpa sertifikat tetap pelanggaran.**
> Dua hal ini berbeda dan Reviewer harus membedakannya.

## 2. Empat produk (status halal sengaja berbeda)

| SKU | Produk | Status halal | Dipakai untuk |
|---|---|---|---|
| AY-SR-101 | Bright Serum (30 ml) | **BELUM ADA** — diajukan 12 Okt 2026 | Hero launch; semua klaim halal harus ditolak |
| AY-BL-102 | Glow Body Lotion (250 ml) | **AKTIF** s/d 2029-03-09 | Kontrol positif: klaim halal boleh |
| AY-FW-103 | Gentle Cleanser (100 ml) | **PENGAJUAN** — belum terbit | Hampir sama dengan hero, beda alasan |
| AY-SC-104 | Coffee Scrub (200 g) | **KEDALUWARSA** 2026-08-31 | Jebakan: nomor ada, tapi tidak berlaku |

## 3. Struktur

```
dataset_c/
├── products.csv                  ← registri produk (dipakai Reviewer)
├── izin_edar.csv                 ← notifikasi/izin edar per produk (R-16)
├── izin_produksi.csv             ← izin produksi per kategori (R-17)
├── sertifikat_klaim.csv          ← USDA organic, dermatologically tested, SPF (R-18/R-19)
├── batas_pengawet.csv            ← batas kadar pengawet per bahan (R-21)
├── komposisi_produk.csv          ← komposisi INCI lengkap per SKU
├── certificates.csv              ← sertifikat halal (R-03)
├── product_sheets/               ← PS-101..104: sumber fakta + kemasan + tulisan label
├── rulebook_claims.md            ← R-01..R-21: dasar penolakan Reviewer
├── brand_tone_guide.md           ← nada merek + anti-pola
├── platform_specs.md             ← batas TikTok / Instagram / marketplace
├── briefs/BRF-101_*.md           ← brief launch (memuat 5 jebakan)
├── approved_content_history/     ← contoh konten yang pernah disetujui
└── sample_drafts/                ← 3 platform, tiap platform punya siklus tolak → lolos
```

## 3b. Alur legalitas sebelum konten boleh menyebut produk "legal"

Urutan ini yang diperiksa Reviewer lapis awal (`engine/audit_kemasan.py`) sebelum
konten ditulis. Melewati satu langkah berarti konten tidak boleh mengklaimnya.

| # | Tahap | Cakupan | Berkas | Aturan |
|---|---|---|---|---|
| 1 | **Notifikasi/izin edar BPOM** | per produk | `izin_edar.csv` | R-16 |
| 2 | **Izin produksi (CPKB)** | per kategori | `izin_produksi.csv` | R-17 |
| 3 | **Sertifikat halal** | produk **dan** pabriknya | `certificates.csv` | R-03 |
| 4 | **Sertifikat klaim khusus** | organik (USDA), uji dermatologis, SPF | `sertifikat_klaim.csv` | R-18, R-19 |

> **Catatan istilah.** Kosmetik memakai **nomor notifikasi** berawalan `NA`, bukan
> "izin edar". Istilah izin edar dipakai untuk kategori lain (obat, suplemen, pangan).
> Kolom `jenis` di `izin_edar.csv` membedakannya supaya tidak tercampur.
>
> **Catatan CPKB.** Di lapangan CPKB bersifat fasilitas, bukan per kategori. Kolom
> `kategori` di `izin_produksi.csv` mengikuti model tim (izin produksi per kategori)
> dan dipakai untuk ketertelusuran.

## 3c. Pemeriksaan kemasan (layer reviewer awal)

`engine/audit_kemasan.py` memeriksa **produk**, bukan draf:

```bash
cd engine && python audit_kemasan.py --semua
```

Yang diperiksa: notifikasi masih berlaku, izin produksi kategori masih berlaku,
nomor BPOM tercetak di label, komposisi & peringatan tercetak, nomor sertifikat
kedaluwarsa yang masih tercetak, dan kadar pengawet terhadap `batas_pengawet.csv`.

Hasil pada dataset ini: tiga produk bersih; **AY-SC-104 punya 3 masalah** (notifikasi
kedaluwarsa, izin produksi kategori kedaluwarsa, nomor halal kedaluwarsa masih tercetak).
Itu sengaja — satu SKU "bermasalah" membuat setiap aturan punya kasus uji nyata.

## 4. Cara pakai untuk tim

| Peran | Memakai apa |
|---|---|
| **Planner** | `briefs/`, `product_sheets/`, `platform_specs.md` |
| **Writer** | kerangka Planner + `product_sheets/` + `brand_tone_guide.md` |
| **Reviewer** | draf Writer + `rulebook_claims.md` + `products.csv` + registri legalitas + `sample_drafts/` |

`sample_drafts/` ada supaya **Reviewer bisa diuji tanpa Writer**. v1 → v2 → v3 adalah
siklus tolak → perbaiki → setujui yang diminta handbook.

### Cakupan platform (syarat handbook: minimal dua)

| Platform | Draf | Temuan v1 | Status v2 |
|---|---|---|---|
| TikTok | `DRAFT-101_v1/v2/v3` | 14 | lolos di v3 |
| Instagram | `DRAFT-101-ig_v1/v2` | 9 | lolos |
| Marketplace | `DRAFT-101-mkt_v1/v2` | 8 | lolos |

Aturan yang **berbeda per platform** dan diuji terpisah:
- **Instagram** — hashtag berklaim (`#halal`) dihitung sebagai klaim (R-03), batas 2200 karakter
- **Marketplace** — nomor BPOM wajib (R-02), judul ≤70 karakter tanpa emoji (R-06/R-10)
- **TikTok** — naskah ≤±150 kata, maksimal 2 emoji (R-10)

## 5. Verifikasi silang ke BPJPH

`engine/bpjph_client.py` bisa mengecek nomor sertifikat ke registri publik BPJPH.
Kosmetik memakai kode jenis **D0001**. Nomor sertifikat asli berformat
`ID` + 17 digit dan **dua digit terakhir = tahun terbit**
(mis. `ID32110019969360724` → terbit 2024).

Reviewer memakai ini untuk membedakan tiga hal yang sering dicampur:
nomor **ada**, nomor **berlaku**, dan nomor **mencakup produk ini**.

## 6. Data registri nyata — `real_registry_samples.csv`

Berkas ini berisi **9 nomor sertifikat kosmetik yang benar-benar ada** di registri publik
BPJPH (ditarik 30 Okt 2026, semua `jenis_produk D0001`).

> **Penting — bedakan dua hal:**
> - Produk Ayunika (PS-101..104) = **fiktif**, nomor sertifikat **mock**.
> - `real_registry_samples.csv` = **data publik nyata**, hanya untuk mendemokan verifikasi.
>
> **Jangan** menempelkan nomor nyata ke lembar produk fiktif. Itu mengatribusikan sertifikat
> perusahaan lain ke produk yang tidak ada.

### Temuan yang mengubah desain Reviewer

Satu nomor sertifikat bisa mencakup **ratusan produk dari puluhan merek**:

| Nomor | Produk tercakup |
|---|---|
| `ID32110019969360724` | **306 produk** — PT Janing Dermagio Kosmetik |
| `ID00210014216071123` | 22 merek dalam satu sertifikat (PT Larassanti) |

Ini model **maklon/OEM**: sertifikat diterbitkan ke pabrik, dan banyak merek memakai
formulasi yang sama. Konsekuensinya untuk R-03:

> Merek berada di bawah sertifikat yang sama **bukan** otomatis berarti merek itu tercakup.
> Yang harus diperiksa: apakah SKU/merek tersebut memang terdaftar.

### Demo verifikasi yang disarankan

| Yang diuji | Hasil | Untuk menunjukkan |
|---|---|---|
| `ID32110019969360724` (nyata) | ditemukan, 306 produk | mekanisme verifikasi bekerja |
| `ID32110084875141025` (mock Ayunika) | tidak ditemukan | nomor palsu tidak lolos |

Jalankan: `python engine/reviewer.py verify <nomor>` atau `Reviewer().verify_external(nomor)`.

