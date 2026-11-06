# mcp_server — Lolos sebagai MCP server

Lapisan tipis di atas `engine/` dan `agents/`. Tidak ada aturan review yang
ditulis ulang di sini: `engine/reviewer.py` tetap satu-satunya penilai dan
`engine/governance.py` tetap satu-satunya gerbang approval.

```
WorkBuddy  ──stdio──▶  mcp_server/stdio.py
           ──https──▶  mcp_server/http.py  ──▶  AuthMiddleware ──▶ /mcp
                            │
                            ▼
                       mcp_server/server.py    19 tool, tanpa logika
                            │
                            ▼
                       mcp_server/tools.py     fungsi biasa, tanpa impor mcp
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  agents/planner.py   agents/writer.py    engine/reviewer.py
                                          engine/governance.py
```

Dua transport, satu permukaan tool. `stdio.py` dipakai untuk lokal; `http.py`
dipakai saat server punya URL publik. Keduanya mengimpor `server.py` yang sama,
jadi tidak ada tool yang hanya ada di salah satu jalur.

## Menjalankan

```powershell
# sekali saja
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
```

Konfigurasi WorkBuddy ada di `~/.workbuddy-ai/mcp.json`. Contoh tanpa rahasia:
`mcp.example.json`.

## Menguji

```powershell
# logika, tanpa protokol — 67 pemeriksaan
.\.venv\Scripts\python.exe -m mcp_server.run_tests

# protokol sungguhan: handshake, list_tools, call_tool lewat stdio
.\.venv\Scripts\python.exe -m mcp_server.smoke_client

# transport HTTP sungguhan: server terpisah, 401, 421, klien SDK
.\.venv\Scripts\python.exe -m mcp_server.test_http

# bukti tidak ada regresi di engine
cd engine; ..\.venv\Scripts\python.exe run_reviewer_tests.py   # 73/73
```

Ketiganya mengalihkan rantai audit ke folder sementara lewat `HALAL_AUDIT_DIR`,
supaya `engine/.audit/audit.jsonl` tidak tercemar entri uji.

## Dua belas tool

| Tool | Kegunaan |
|---|---|
| `list_products` | SKU, harga, promo, BPOM, status halal |
| `get_context` | lembar produk, brief, sertifikat, batas platform |
| `get_rulebook` | R-01..R-21 dan lapis pemeriksanya |
| `plan_content` | rencana tervalidasi dari lembar produk |
| `validate_plan` | periksa bentuk rencana |
| `write_draft` | tulis draf dari rencana |
| `review_draft` | verdict + temuan + kutipan |
| `run_cycle` | Planner → Writer → Reviewer, maks 3 iterasi |
| `audit_verify` | telusuri rantai hash |
| `audit_tail` | n entri terakhir (maks 100) |
| `request_approval` | usul ke gerbang → `PROPOSED` |
| `approve_publication` | setujui satu plan → `APPROVED` (approver diturunkan dari kunci) |

## Gerbang approval

```
request_approval  →  PROPOSED
approve_publication (kunci manusia → nama approver diturunkan)  →  APPROVED
                                                                   │
                                                                berhenti
```

Tidak ada `execute_publication`. Rantai berhenti di `APPROVED`; tidak ada
callback publikasi di server ini.

### Kunci per approver

Satu kunci per manusia, dan server **hanya menyimpan SHA-256 hex kuncinya** —
bukan kunci aslinya. Nama approver **diturunkan** dari kunci yang dikirim;
pemanggil tidak bisa mengaku siapa pun. Dengan itu "approver ≠ pemohon" di
`ApprovalGate` menjadi terbukti: agen tidak bisa menghasilkan kunci manusia
kedua, jadi swa-approval mustahil, bukan sekadar dilarang lewat nama bebas.

Buat kunci + hash-nya:

```
python -m mcp_server.gen_approver_keys Agung Budi
```

Pasang hasilnya sebagai `MCP_APPROVER_KEYS` (env) atau berkas `.approver_keys`
di root repo — keduanya JSON `{"Nama": "<sha256>"}`. `.approver_keys` sudah
masuk `.gitignore`. Rotasi = jalankan ulang untuk nama yang sama, ganti hash-nya;
perhatikan bahwa restart server mengosongkan plan `PROPOSED` di memori.

Jalur legacy masih jalan: `MCP_APPROVAL_KEY` + `MCP_APPROVAL_KEY_OWNER`
(wajib — kunci lama tanpa nama pemilik ditolak, bukan diam-diam dijadikan
identitas bebas). Nilai di registri harus sha256 hex; menempel kunci asli
tertangkap dan ditolak dengan pesan yang menyebut nama pemiliknya.

Tanpa registri yang sah, `approve_publication` mengembalikan
`approval_belum_dikonfigurasi` dan tidak ada yang bisa lolos gerbang.

`ApprovalGate` menolak:

- approver yang diturunkan dari kunci sama dengan pemohon (`workbuddy-agent`)
- plan yang statusnya bukan `PROPOSED` (approval kedua)
- `plan_id` yang tidak ada
- kunci yang tidak cocok dengan approver mana pun

Setiap penolakan di atas juga **tercatat** sebagai `approval_blocked` /
`REFUSED` di rantai audit, lengkap dengan alasannya. Tanpa itu, tebakan kunci
berulang tidak meninggalkan jejak apa pun — log tetap terlihat bersih padahal
seseorang sedang mencoba memaksa gerbang. Kunci yang dicoba tidak pernah ikut
tercatat; yang masuk hanya nama approver, plan_id, dan alasannya.

Plan disimpan di memori. Restart server menghapusnya; rantai audit tetap utuh.

## Batas yang perlu diketahui

- **`PERLU_DATA` bukan lulus.** Artinya tidak ada pelanggaran terdeteksi, tetapi
  data produk tidak cukup untuk memverifikasi. Untuk SKU yang tidak ada di
  registri, verdict ini yang keluar — bukan `LOLOS`.
- **Kutipan lapis-2 diverifikasi.** `findings` dari model pemanggil hanya
  diterima bila `span` benar-benar ada di draf; sisanya masuk `dibuang_llm`.
- **Keluaran berupa teks JSON.** Anotasi `-> dict` tidak menghasilkan output
  schema, jadi SDK mengirim payload sebagai `content[0].text`, bukan
  `structuredContent`. Semua host MCP bisa membacanya.
- **Tanpa LLM di dalam tool.** Planner dan Writer berjalan deterministik, supaya
  setiap panggilan selesai jauh di bawah timeout 30 detik WorkBuddy.
- **Satu proses.** `AuditLog` mengasumsikan satu penulis dan `ApprovalGate`
  hidup di memori. Jangan jalankan lebih dari satu worker.

## Path B — server publik

`http.py` menyajikan Streamable HTTP di `/mcp` dengan bearer token, `/health`
tanpa token, dan allowlist Host. `__main__.py` menjalankan uvicorn dengan satu
worker.

```powershell
$env:MCP_TOKEN = "token-panjang"
$env:MCP_APPROVAL_KEY = "kunci-lain-lagi"
$env:MCP_ALLOWED_HOSTS = "mcp.contoh.com"
.\.venv\Scripts\python.exe -m mcp_server
```

Tanpa `MCP_ALLOWED_HOSTS`, hanya host lokal yang diterima dan permintaan dari
domain publik dibalas `421 Misdirected Request`.

Langkah deploy lengkap — systemd, nginx + certbot, Cloudflare Tunnel, Docker —
ada di [`deploy/README.md`](../deploy/README.md).
