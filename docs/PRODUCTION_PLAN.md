# Production Plan — Ayunika Content Reviewer

**Status:** rencana, belum dieksekusi
**Tanggal:** 30 Okt 2026 · **Deadline submission:** 1 Nov 2026 · **Demo Day:** 27 Nov 2026

---

## 0. Tiga prinsip yang tidak boleh dilanggar

Semua keputusan teknis di bawah turun dari tiga prinsip ini. Kalau salah satu dilanggar,
produknya berubah jadi berbahaya.

| Prinsip | Artinya | Konsekuensi teknis |
|---|---|---|
| **Fail closed** | Kalau LLM mati / timeout / output tidak valid → konten **tidak terbit** | Tidak ada fallback ke "anggap lolos". Error → status `REVIEW_INCOMPLETE` → eskalasi |
| **Deterministic-first** | Aturan yang bisa dicek kode dicek kode, bukan model | LLM tidak pernah jadi satu-satunya penentu; lapis kode jalan lebih dulu |
| **Human-in-the-loop** | Publikasi selalu butuh `plan_id` APPROVED | Tidak ada jalur otomatis, termasuk untuk admin |

---

## 1. Definisi "production" untuk proyek ini

**Yang termasuk:**
- Satu instance, satu tenant (tim marketing Ayunika), dipakai internal
- 3 endpoint API: kirim brief, lihat hasil review, setujui/tolak
- Audit trail yang bisa diperiksa ulang

**Yang TIDAK termasuk** (jangan dikerjakan dulu — ini yang membuat proyek gagal):
- Multi-tenant / SaaS berlangganan
- Billing, kuota per pelanggan
- Aplikasi mobile
- Auto-publish ke Instagram/TikTok API

> Menulis batas ini di README akan menyelamatkanmu dari pertanyaan "kok belum ada X?" saat demo.

---

## 2. Fase 0 — Selamatkan submission dulu (30 Okt – 1 Nov)

**Jangan sentuh arsitektur sebelum 1 November.** Pekerjaan production bisa merusak
submission yang sudah jalan (25/25 tes lulus).

| Tanggal | Yang dikerjakan | Yang TIDAK dikerjakan |
|---|---|---|
| 30 Okt (hari ini) | Push repo **private**, tulis README, rapikan `.gitignore` | Refactor folder, ganti framework |
| 31 Okt | Jalankan 25 tes, rekam demo 8 menit, isi `02_test_results.md` | Menyambung LLM sungguhan |
| 1 Nov | Isi 7 template submission, submit | Apa pun yang mengubah kode inti |

Sisa fase di bawah ini **dikerjakan setelah 1 Nov**, sebelum Demo Day 27 Nov.

---

## 3. Fase 1 — Repository GitHub

### 3.1 Apa yang di-push

| Path | Push? | Alasan |
|---|---|---|
| `engine/*.py` | ✅ | Kode inti (reviewer, pipeline, governance, bpjph_client) |
| `dataset_c/` (kecuali yang di bawah) | ✅ | Dataset inti Challenge C |
| `dataset_c/real_registry_samples.csv` | ✅ | Data publik BPJPH, sudah terbuka |
| `diagram/architecture_challenge_c.svg` + `.py` | ✅ | Sumber vektor + generator |
| `submission_templates/` | ✅ | Bukti proses hackathon |
| `research/DEEP_RESEARCH_*.md` | ✅ | Menunjukkan dasar keputusan |
| `README.md`, `LICENSE`, `.gitignore`, `.env.example` | ✅ | Wajib |

### 3.2 Apa yang JANGAN di-push

| Path | Kenapa |
|---|---|
| `dataset_halal/shared/contacts.csv` | Memuat **NIK dan nomor telepon** (mock, tapi formatnya nyata). Jangan pernah publikasikan |
| `dataset/shared/contacts.csv` | Sama — dataset resmi panitia, juga berisi NIK |
| `engine/.cache_bpjph/` | Hasil scraping, 2,9 MB, state runtime |
| `engine/.audit/audit.jsonl` | State runtime, terus bertambah, memuat ID aktor |
| `Handbook_*.pdf` (2 file) | Materi panitia, bukan milikmu untuk dipublikasikan |
| `research/src/*.pdf` | PDF regulasi pihak ketiga, ukuran besar |
| `.env`, `*.key`, `secrets.*` | Kredensial |
| `diagram/*.png` | Bisa diregenerasi dari `.py`; simpan di Releases kalau perlu |

> **Soal NIK:** meskipun mock, `contacts.csv` terlihat seperti data pribadi nyata. Kalau
> repo publik dan ada yang mengira itu bocoran, reputasimu yang kena. Kalau butuh contoh
> kontak, ganti NIK jadi `0000000000000000` dan telepon jadi `+62-000-000-0000`.

### 3.3 `.gitignore` minimal

```gitignore
# state runtime
engine/.audit/
engine/.cache_bpjph/
*.sqlite
*.db

# kredensial
.env
.env.*
!.env.example
*.key
secrets.*

# data pribadi
**/contacts.csv

# artefak
__pycache__/
*.pyc
.venv/
node_modules/
dist/
build/
```

### 3.4 Struktur target (setelah 1 Nov)

Sekarang kode masih rata di `engine/`. Untuk production, susun begini — **migrasi mekanis,
bukan tulis ulang**:

```
ayunika-reviewer/
├── README.md
├── LICENSE                    (MIT untuk kode; data terpisah)
├── .gitignore
├── .env.example
├── pyproject.toml
├── Makefile                   (make test / make run / make seed)
├── docs/
│   ├── PRODUCTION_PLAN.md     ← dokumen ini
│   ├── ARCHITECTURE.md
│   └── RULEBOOK.md
├── src/ayunika/
│   ├── config.py              (baca env, validasi saat start)
│   ├── llm/
│   │   ├── client.py          (abstraksi provider)
│   │   ├── schemas.py         (pydantic: PlanOut, FindingOut)
│   │   └── prompts/
│   │       ├── planner_v1.md
│   │       ├── writer_v1.md
│   │       └── reviewer_v1.md
│   ├── agents/
│   │   ├── planner.py
│   │   ├── writer.py
│   │   └── reviewer.py        ← sudah ada, pindah saja
│   ├── governance/
│   │   ├── audit.py           ← sudah ada
│   │   └── approval.py        ← sudah ada
│   ├── pipeline.py            ← sudah ada
│   └── api.py                 ← baru
├── data/
│   ├── products.csv
│   ├── certificates.csv
│   ├── rulebook_claims.md
│   └── product_sheets/
└── tests/
```

### 3.5 Perintah awal

```bash
git init
git add .
git commit -m "chore: initial import (Challenge C reviewer)"
gh repo create ayunika-reviewer --private --source=. --push
```

**Private dulu.** Publik setelah 1 Nov, setelah `contacts.csv` dibersihkan.

---

## 4. Fase 2 — Menyambung LLM

### 4.1 Di mana LLM dipanggil

```
Brief ──► PLANNER ──► LLM call #1 (structured JSON)
            │
            ▼
         WRITER ────► LLM call #2 (teks panjang)   ┌── maks 3 putaran
            │                                       │
            ▼                                       │
         REVIEWER ──► (a) cek kode — tanpa LLM      │
                      (b) LLM call #3 (judgment) ───┘
            │
            ▼
      APPROVAL MANUSIA ──► PUBLISH
```

**Penting:** Reviewer memanggil LLM **setelah** cek kode. Kalau cek kode sudah menemukan
pelanggaran berat, putaran itu tetap harus jalan — tapi hemat biaya dengan mengirim hanya
bagian draf yang belum tertangkap.

### 4.2 Abstraksi provider — jangan hardcode

```python
# src/ayunika/llm/client.py
from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, *, schema: dict | None = None,
                 max_tokens: int = 2000, timeout: int = 30) -> dict | str: ...

class ProviderX(LLMClient):
    def complete(self, system, user, *, schema=None, max_tokens=2000, timeout=30):
        # panggil API; kalau schema → pakai mode JSON/structured output
        ...
```

Alasannya: harga dan kualitas model berubah tiap kuartal. Kalau provider dikunci di 20 tempat,
migrasi jadi mimpi buruk.

### 4.3 Structured output + validasi

Planner dan Reviewer **wajib** keluaran JSON yang divalidasi. Tanpa ini, `apply_llm_findings`
akan menerima sampah.

```python
from pydantic import BaseModel, ValidationError

class Finding(BaseModel):
    rule_id: str
    span: str          # kutipan persis dari draf
    reason: str
    fix: str

class ReviewOut(BaseModel):
    findings: list[Finding]
```

Alur: panggil → parse JSON → validasi pydantic → **verifikasi span ada di draf** →
baru diterima. Gagal di langkah mana pun → retry sekali → masih gagal → `REVIEW_INCOMPLETE`.

### 4.4 Tiga prompt yang harus kamu tulis

| Prompt | Keluaran | Panjang | Catatan |
|---|---|---|---|
| `planner_v1.md` | JSON rencana per platform | ~500 token | Harus menyebut fakta mana yang dipakai |
| `writer_v1.md` | Teks draf | ~800 token | Menerima `feedback` dari Reviewer |
| `reviewer_v1.md` | JSON findings | ~1200 token | Sudah ada di `reviewer.LLM_PROMPT`, tinggal dipindah ke file |

**Simpan versi prompt di nama file dan catat di log.** Kalau nanti ada konten bermasalah,
kamu bisa menjawab "itu dibuat dengan prompt v1, bukan v2".

### 4.5 Aturan wajib di lapisan LLM

| Aturan | Implementasi |
|---|---|
| **Fail closed** | Exception/timeout → `REVIEW_INCOMPLETE`, jangan `LOLOS` |
| **Timeout** | 30 detik per panggilan, tidak ada retry tak terbatas |
| **Budget** | Maks 9 panggilan per konten (3 agent × 3 iterasi). Lebih dari itu → eskalasi |
| **Idempoten** | Simpan hasil per (brief_id, iterasi, agent) supaya retry tidak dobel tagih |
| **Tidak ada PII di prompt** | Jangan kirim nama/telepon ke provider pihak ketiga |
| **Log prompt hash** | Simpan SHA-256 prompt + versi, bukan isi penuh, untuk audit |

### 4.6 Estimasi biaya

Satu siklus konten ≈ **10–15 ribu token** (planner 1×, writer 3×, reviewer 3×).
Kalau tim membuat 20 konten/bulan → ~300 ribu token/bulan. Hitung dengan tarif provider-mu;
pada tarif kelas menengah ini masih di bawah satu dolar per bulan. **Biaya bukan masalah;
latency dan reliabilitas yang masalah.**

---

## 5. Fase 3 — Backend API

### 5.1 Tiga endpoint saja

| Method | Path | Fungsi |
|---|---|---|
| `POST` | `/v1/reviews` | Kirim brief + SKU + platform → jalankan pipeline → kembalikan hasil |
| `POST` | `/v1/reviews/{id}/approve` | Manusia menyetujui (atau menolak) |
| `GET` | `/v1/reviews/{id}` | Status + riwayat iterasi + temuan + audit trail |

### 5.2 State machine

```
QUEUED → RUNNING → REVIEW_INCOMPLETE → (retry/eskalasi)
                 ├→ REJECTED   (iterasi habis → eskalasi)
                 ├→ PASSED     (menunggu approval)
                 │      ├→ APPROVED → PUBLISHED
                 │      └→ DECLINED
```

`PUBLISHED` hanya bisa dicapai lewat `APPROVED`. Ini dikunci di kode, bukan di UI.

### 5.3 Penyimpanan

| Data | MVP | Production |
|---|---|---|
| Audit log | SQLite (append-only, hash chain) | Postgres + tabel append-only |
| State review | in-memory dict | Postgres |
| Konten final | file | object storage + hash |

Jangan pindah ke Postgres sebelum perlu. SQLite cukup untuk satu tenant.

---

## 6. Fase 4 — Menyambung ke website

### 6.1 Tiga opsi

| Opsi | Cara | Cocok untuk | Risiko |
|---|---|---|---|
| **A. API + UI sendiri** ⭐ | Website memanggil `/v1/reviews`, render sendiri | Kontrol penuh, brand konsisten | Perlu kerja frontend |
| B. Iframe | Host app terpisah, embed | Tercepat | Audit trail terpisah dari situs |
| C. Webhook | Situs kirim konten, terima verdict | Integrasi ke CMS | Tidak ada UI review |

**Rekomendasi: A.** Kamu butuh layar approval yang menampilkan *mengapa* ditolak —
itu justru nilai produknya. Iframe menyembunyikan bagian terbaik.

### 6.2 Alur UX minimal

```
[Form brief] → [Tombol "Review"] → [Progress: Planner ✓ Writer ✓ Reviewer ✓]
   → [Daftar temuan per aturan, dengan kutipan kalimat]
   → [Tombol "Setujui & terbitkan" (disabled kalau TOLAK)]
   → [Riwayat iterasi v1 → v2 → v3]
```

### 6.3 Aturan keamanan frontend

- **API key LLM tidak boleh ada di browser.** Semua panggilan model lewat backend.
- Situs memanggil backend-mu dengan sesi pengguna, bukan dengan key provider.
- CORS: whitelist domain situsmu saja.
- Rate limit per sesi: 10 review/jam.

---

## 7. Fase 5 — Deploy & operasional

| Item | Rekomendasi |
|---|---|
| Hosting | Satu container (FastAPI + SQLite volume). Render/Fly/Railway/VPS kecil |
| Env | `LLM_API_KEY`, `LLM_MODEL`, `APPROVER_EMAIL`, `BPJPH_CACHE_TTL`, `LOG_LEVEL` |
| Start-up check | Aplikasi **menolak start** kalau env wajib kosong |
| Health check | `/healthz` → cek DB + status LLM (tanpa memanggil model) |
| Log | JSON terstruktur, tanpa isi prompt penuh |
| Alert | (a) LLM error rate > 10%, (b) review stuck > 15 menit, (c) audit chain rusak |
| Backup | Audit log harian ke storage terpisah (append-only) |
| Rate limit BPJPH | Cache 24 jam, maks 1 permintaan/detik, User-Agent jelas |

**Soal BPJPH:** endpoint itu tidak resmi dan bisa berubah kapan saja. Di production,
selalu bungkus dengan timeout + fallback: kalau registri tidak bisa diakses, verifikasi
eksternal ditandai `TIDAK_DAPAT_DIVERIFIKASI` — **bukan** dianggap gagal.

---

## 8. Fase 6 — Keamanan & kepatuhan

| Isu | Tindakan |
|---|---|
| **Data pribadi** | `contacts.csv` tidak dipublikasikan; prompt tidak memuat nama/telepon |
| **PP 33/2026** | Mulai **16 Jan 2027** AI yang memproses data pribadi wajib punya penilaian dampak pelindungan data. Kalau produk ini menyimpan data pelanggan, siapkan dokumennya |
| **Data mock vs nyata** | Jangan pernah mencampur nomor sertifikat nyata ke produk fiktif — sudah dijaga di `dataset_c/README.md` |
| **Kredensial** | Rotasi API key sebelum repo dibuat publik; cek `git log` tidak memuat key |
| **Lisensi** | Kode MIT. Dataset turunan BPJPH: sebut sumbernya, jangan klaim sebagai milikmu |
| **Disclaimer** | Di UI dan README: "alat bantu kepatuhan, bukan penentu status halal" |

---

## 9. Fase 7 — Checklist go-live

**Sebelum deploy:**
- [ ] 25 tes lulus di CI
- [ ] `git log` bersih dari key/PII
- [ ] `.env.example` lengkap, `.env` tidak ter-commit
- [ ] Aplikasi menolak start tanpa env wajib
- [ ] Jalur LLM-down diuji manual (matikan key → harus `REVIEW_INCOMPLETE`, bukan `LOLOS`)
- [ ] Approval gate diuji: publish tanpa approve → ditolak

**Saat deploy:**
- [ ] Health check hijau
- [ ] Satu review end-to-end berhasil
- [ ] Audit chain `verify()` → utuh

**Rollback:** simpan image sebelumnya; rollback = redeploy image lama. Karena audit log
append-only, rollback tidak menghilangkan riwayat.

---

## 10. Urutan waktu

| Fase | Kapan | Durasi |
|---|---|---|
| 0. Freeze + submission | 30 Okt – 1 Nov | 2 hari |
| 1. Repo + `.gitignore` | 2 Nov | 2 jam |
| 2. LLM + prompt | 3–5 Nov | 3 hari |
| 3. API + state | 6–7 Nov | 2 hari |
| 4. Frontend | 8–10 Nov | 3 hari |
| 5. Deploy + ops | 11–12 Nov | 2 hari |
| 6. Keamanan + dokumen | 13 Nov | 1 hari |
| 7. Go-live internal | 14 Nov | — |
| Buffer sebelum Demo Day | 15–26 Nov | — |

---

## 11. Yang paling mungkin gagal

Bukan LLM-nya. Yang paling sering menjatuhkan proyek seperti ini:

1. **Prompt dianggap kode yang bisa diedit langsung di production.** Versikan dari awal.
2. **Tidak ada batas iterasi.** Sudah dijaga di `decide_next()`, jangan dilepas.
3. **Reviewer diserahkan penuh ke model.** Penjaga kutipan (`apply_llm_findings`) wajib tetap aktif.
4. **Data mock bocor ke demo nyata.** Satu nomor sertifikat palsu yang diklaim nyata bisa
   menghapus kredibilitas seluruh proyek.
