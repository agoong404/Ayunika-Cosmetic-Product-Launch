# agents/ — Planner & Writer (Challenge C)

Dua peran yang boleh diganti, dipisah dari `engine/` yang menegakkan aturan.

```
engine/   Reviewer · governance · orkestrator     ← jangan diubah sembarangan
agents/   Planner · Writer                        ← boleh diganti tim
```

## Struktur

| Berkas | Isi |
|---|---|
| `contract.py` | Bentuk `Plan`, batas platform, validasi, `ContractError` |
| `planner.py` | `PlannerAgent` — brief + lembar produk → `Plan` |
| `writer.py` | `WriterAgent` — `Plan` + catatan Reviewer → teks |
| `registry.py` | Memilih agent: `mine` / `team` / `stub` / skenario rusak |
| `harness.py` | 40 run, 4 skenario, pelacakan error + invarian |
| `test_wiring.py` | Bukti jalur LLM tersambung (pakai klien palsu, tanpa API key) |
| `llm/client.py` | Pemanggil model: provider apa pun yang OpenAI-compatible |
| `llm/prompts/` | `planner_v1.md`, `writer_v1.md` — prompt berversi |
| `contoh_agent_tim.py` | Cetakan untuk agent rekan tim |
| `workbuddy.py` | Jembatan WorkBuddy: loop tanpa API key |
| `WORKBUDDY.md` | Cara memakai jembatan itu |
| `../.workbuddy-ai/skills/` | Tiga skill WorkBuddy: `lolos-planner` · `lolos-writer` · `lolos-reviewer` |

Reviewer lapis-2 (penilaian model) ada di `engine/layer2.py` + `engine/prompts/reviewer_lapis2_v1.md`,
karena ia bagian dari peran Reviewer — bukan peran yang boleh diganti.

## Tiga perintah untuk mulai

```bash
cd "C:/.Hackathon Project"

python -m agents.planner AY-SR-101 tiktok     # lihat rencana yang dihasilkan
python -m agents.writer  AY-SR-101 tiktok     # lihat draf
python -m agents.harness                      # 40 run, semua skenario
```

Tidak butuh API key. Tanpa key, agent berjalan deterministik.

## Kontrak

```python
planner(brief: str, sku: str, platform: str) -> Plan | dict
writer(plan: Plan, feedback: list[dict] | None, iterasi: int) -> str
```

`feedback` berisi temuan Reviewer:

```json
[{"rule_id": "R-07", "span": "kutipan dari draf", "reason": "...", "fix": "...", "layer": "deterministik"}]
```

Semua keluaran divalidasi **sebelum** masuk pipeline. Agent yang mengembalikan
bentuk salah gagal dengan pesan yang menyebut field mana yang kurang — bukan
`KeyError` di tengah loop.

## Mengganti dengan agent rekan tim

```bash
# 1. salin cetakannya, isi logikanya
cp agents/contoh_agent_tim.py tim/agents.py

# 2. jalankan dengan agent tim
TEAM_AGENTS_MODULE=tim.agents python -m agents.harness --agents team
```

Modul tim cukup menyediakan dua fungsi bernama `planner` dan `writer`
(atau kelas `PlannerAgent` / `WriterAgent`). Tidak perlu menyentuh `engine/`.

## Hasil 40 run (tanpa LLM)

```
total run      : 40
lulus          : 40
exception lolos: 0

cabang loop    : normal→TERBIT 12 · scripted→TERBIT 4 · stubborn→ESKALASI 12 · crash→GAGAL 12
distribusi     : iterasi 1 = 12 · iterasi 2 = 14 · iterasi 3 = 14
rantai audit   : UTUH (252 entri)
```

Empat skenario itu ada bukan untuk gaya-gayaan, tapi supaya setiap cabang loop
benar-benar terlewati:

| Skenario | Yang diuji | Harapan |
|---|---|---|
| `normal` | Planner + Writer bawaan | TERBIT di iterasi 1 |
| `scripted` | Draf manusia v1→v2→v3 (14→4→0 temuan) | TERBIT, 2–3 iterasi |
| `stubborn` | Writer yang tidak pernah memperbaiki | **ESKALASI**, bukan terbit |
| `crash` | Writer melempar exception di iterasi 2 | **GAGAL**, bukan exception mentah |

Satu run sengaja diulang identik untuk memastikan hasilnya deterministik.

### Yang ditemukan harness ini

Tiga hal yang tidak akan terlihat tanpa menjalankan 40 kali:

1. **Exception agent menjatuhkan proses.** `pipeline.run()` dulu membiarkan error
   Writer lolos ke pemanggil. Sekarang setiap tahap dibungkus: status `GAGAL`,
   alasan tercatat di audit log, dan tidak ada yang terbit.
2. **Skenario uji yang tidak menguji apa pun.** `stubborn` dan `crash` awalnya
   ditumpuk pada Writer yang sudah patuh — hasilnya selalu TERBIT di iterasi 1,
   jadi cabang eskalasi dan error tidak pernah tercapai. Harness menandainya
   sebagai "status TERBIT != harapan", dan itu benar.
3. **Draf platform tertukar.** Skenario `scripted` memakai draf TikTok untuk
   Instagram dan marketplace, menghasilkan temuan palsu (15/5/1). Sekarang draf
   dipilih per platform.

## Dua jalur menyambung model

| Jalur | Butuh API key | Untuk apa | Mulai dari |
|---|---|---|---|
| **WorkBuddy** (percakapan + berkas) | tidak | demo, submission, kerja manual | `agents/WORKBUDDY.md` |
| **API provider** (HTTP) | ya | backend website, volume besar | bagian di bawah |

Jalur WorkBuddy sudah diuji dan menghasilkan siklus nyata: draf agensi ditolak
dengan 6 temuan (R-03, R-07, R-14×2, R-06, R-09), lalu lolos di iterasi 2.

```bash
python -m agents.workbuddy start AY-SR-101 tiktok
python -m agents.workbuddy save plan  <berkas.json>
python -m agents.workbuddy next
python -m agents.workbuddy save draft <berkas.md>
```

## Tiga skill WorkBuddy

Siklus yang sama tersedia sebagai **tiga skill terpisah** di `.workbuddy-ai/skills/`,
supaya tiap peran bisa dipanggil sendiri tanpa menghafal urutan perintah:

| Skill | Peran | Menyerahkan ke |
|---|---|---|
| `lolos-planner` | brief → rencana tervalidasi (`agents/.wb/jawaban-plan.json`) | `lolos-writer` |
| `lolos-writer` | rencana + catatan → draf; mengirim lewat `save draft` | `lolos-reviewer` |
| `lolos-reviewer` | lapis-1 + lapis-2 → verdict; TOLAK kembali ke Writer | `lolos-writer` / gerbang approval |

Ketiganya tersambung lewat **state sesi yang sama** (`agents/.wb/session.json`), bukan
lewat saling memanggil langsung: Planner menulis rencana → Writer membacanya → Reviewer
membaca draf terakhir. Karena itu `status` selalu menunjukkan di mana rantai berada.

Yang membedakan skill dari sekadar pembungkus CLI: tiap skill membawa batas perannya.
`lolos-writer` dilarang membuka rulebook; `lolos-reviewer` dibatasi enam aturan lapis-2
dan wajib mengutip teks draf. Batas itu tertulis di `SKILL.md`, bukan di kepala orang.

## Menyambungkan LLM (jalur API)

### 1. Siapkan konfigurasi

```bash
cp agents/.env.example agents/.env
# isi LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
set -a && source agents/.env && set +a
```

### 2. Uji satu panggilan dulu

```bash
python -m agents.llm.client --ping
```

Jangan lewati langkah ini. Ia memberi tahu apakah base URL, path, key, dan nama
model benar — sebelum kamu menghabiskan waktu pada 40 run yang semuanya gagal.

Kalau `404`, kemungkinan `LLM_CHAT_PATH` berbeda untuk provider-mu.
Kalau `401/403`, key atau hak akses modelnya salah.

### 3. Jalankan ulang

```bash
python -m agents.planner AY-SR-101 tiktok    # mode: llm
python -m agents.harness                     # 40 run dengan model
```

### 4. Ukur kualitasnya, bukan hanya "jalan"

Yang perlu kamu hitung setelah 5–10 draf nyata:

| Metrik | Cara | Ambang |
|---|---|---|
| Rata-rata iterasi sampai lolos | `harness` → distribusi iterasi | ≤ 2 bagus, 3 sering = Writer lemah |
| Temuan lapis-2 diterima vs dibuang | `Reviewer.dropped_llm` | diterima ≥ 70% |
| Draf yang gagal kontrak | `ContractError` di harness | 0 |

Kalau model sering salah mengutip, temuannya banyak dibuang penjaga span, dan
Reviewer melemah bukan karena logikanya — tapi karena modelnya tidak bisa mengutip.
Itu alasan mengganti model, bukan mengganti arsitektur.

## Batas yang perlu diketahui

- **Mode deterministik tidak bisa "kalah".** Writer deterministik hanya menyalin
  klaim yang diizinkan, jadi ia hampir selalu lolos di iterasi 1. Itu bukan bukti
  sistemnya pintar — itu bukti ia konservatif. Nilai sesungguhnya baru muncul saat
  LLM menulis kalimat yang manusiawi dan Reviewer menahannya.
- **Lapis-2 Reviewer sudah tersambung, tapi belum diuji dengan provider sungguhan.**
  Jalurnya ada (`engine/layer2.py`, `Layer2.run()`), penjaga kutipannya ada, dan 9 asersi
  lapis model lulus dengan klien palsu. Yang belum: kualitas keluaran model nyata.
- **`crash` dan `stubborn` adalah kerusakan yang disengaja.** Keduanya bukan agent
  sungguhan; keduanya ada untuk membuktikan orkestrator tidak runtuh saat agent gagal.
