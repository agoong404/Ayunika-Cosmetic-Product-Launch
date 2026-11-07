# Situs publik Ayunika Care

Console review untuk pengunjung: pilih SKU, jalankan siklus Planner → Writer →
Reviewer, lihat verdict beserta kutipan temuannya, lalu ajukan ke gerbang
approval. **Persetujuan tetap milik manusia**, dari sesi WorkBuddy — situs ini
tidak memegang kunci approver.

```
Browser  →  BFF (Node, token di sini)  →  MCP di Railway
```

## Kenapa ada BFF

1. `MCP_TOKEN` tidak boleh ada di browser. Di frontend, token = publik.
2. MCP adalah JSON-RPC di atas streamable HTTP (SSE) — canggung dari halaman,
   sepele dari server.
3. Hanya lima tool yang dijangkau pengunjung: `list_products`, `get_rulebook`,
   `run_cycle`, `request_approval`, `audit_tail`. `approve_publication` **tidak
   ada** di berkas BFF — bukan sekadar diblokir, memang tidak ditulis.

Karena BFF memegang `MCP_TOKEN` tapi bukan kunci approver, kebocoran token
transport tidak sama dengan kebobolan gerbang: `approve_publication` tetap
menolak tanpa kunci manusia.

## Tool yang dijangkau pengunjung

Enam tool (semua read-only kecuali `request_approval` yang hanya mengajukan):

| Tool | Dipakai oleh |
|---|---|
| `list_products` | dropdown SKU |
| `get_rulebook` | teks aturan di tiap temuan |
| `run_cycle` | console review (Planner → Writer → Reviewer) |
| `review_draft` | **Bukti penolakan** — pengunjung tempel draf bebas, langsung dapat TOLAK/LOLOS beserta kutipan & perbaikan |
| `request_approval` | ajukan draf yang lolos ke gerbang approval |
| `audit_tail` | cek status plan (PROPOSED/APPROVED/REJECTED) |

`review_draft` sengaja diekspos supaya penolakan terlihat di situs, bukan hanya
di balik sesi WorkBuddy. Ia read-only (lapis deterministik, tanpa LLM) dan tidak
menulis rantai audit — jadi tidak menambah entri approval palsu.

## Jalankan lokal

Tanpa dependensi — tidak perlu `npm install`.

```bash
cd web
export MCP_URL="https://<host-railway>/mcp"
export MCP_TOKEN="<token-transport>"
export PORT=8080
node server/index.js
```

Buka `http://localhost:8080`.

## Tim Ahli di halaman

Panel "Tim Ahli — empat agen" di-parse dari paket expert
`expert/ayunika-compliance-team/` (bukan di-hardcode). Skrip
`scripts/build-team.js` membaca `plugin.json` + `agents/*.md`, lalu menulis
`public/team.json` dan menyalin avatar ke `public/avatars/`. Frontend memanggil
`/team.json` dan merender kartu (nama, peran, bio, alat MCP per agen).

Karena Dockerfile web membangun dari konteks `web/` saja, hasil parse
(`public/team.json` + `public/avatars/*.png`) sudah di-commit dan disajikan
statis. Jika paket expert berubah, jalankan:

```bash
npm run build:team
```

Lalu commit hasilnya. Avatar tim (`team.png`, ikon biru perisai + ceklis) dan
potret tiap anggota diambil langsung dari paket expert.

## Batas yang perlu diketahui

| Hal | Nilai |
|---|---|
| Aturan diperiksa | 15 dari 21 (lapis deterministik) |
| Lapis model | 6 aturan, hanya di alur WorkBuddy (`review_draft` + `findings`) |
| Jatah per IP | 5 review/jam, 10 pengajuan/jam |
| Penyimpanan jatah | memori proses — hilang saat restart |
| Persetujuan | hanya dari WorkBuddy, dengan kunci approver |

Enam aturan lapis-2 sengaja tidak dijalankan di sini: `run_cycle` memanggil
`review_draft` tanpa `findings`, jadi server hanya menilai lapis deterministik.
Kalau nanti ingin lengkap, tambahkan satu panggilan model di BFF lalu kirim
hasilnya sebagai `findings` — seam-nya sudah ada di kontrak MCP.

## Masukan: pilihan, bukan teks bebas

Pengunjung memilih sudut cerita dari empat tombol. Tidak ada pemrosesan bahasa
sama sekali — daftar `SUDUT_PILIHAN` di BFF adalah satu-satunya masukan yang sah,
dan `/api/run` memvalidasi `angle` terhadap daftar itu juga (bukan hanya UI).

Teks bebas tetap boleh dikirim, tetapi **ditolak** dengan pesan yang jelas:

> Maaf, hanya empat pilihan itu yang bisa dipakai. Silakan pilih salah satu
> tombol di atas.

Sengaja tidak ada tebakan kata kunci. Menebak membuat pengunjung mengira sistem
memahami permintaan bebas, padahal tidak — lebih jujur menolak.

"Kenapa ini ditolak" tetap terjawab tanpa model: setiap temuan menampilkan teks
aturan aslinya lewat `get_rulebook`, kutipan persis, dan perbaikannya.

Tidak ada LLM di mana pun dalam berkas ini. Tidak ada kunci model, tidak ada
biaya per pesan, tidak ada permukaan prompt injection.

## Deploy

**BFF** — Railway, service baru dari repo yang sama:

- Root directory: `web`
- Build: Dockerfile (`web/Dockerfile`)
- Start command: `node server/index.js`
- Variables: `MCP_URL`, `MCP_TOKEN` (biarkan `PORT` disuntik Railway)
- Custom domain: set `ayunika-care.web.id` sebagai domain layanan, lalu arahkan
  DNS (CNAME) ke host Railway yang diberikan.

**Frontend** — disajikan BFF sendiri (folder `public/`). Kalau ingin memisah ke
Cloudflare Pages, ubah `fetch("/api/…")` menjadi URL BFF dan tambahkan CORS.

## Jebakan

1. **Jangan taruh `MCP_TOKEN` di `public/`.** Satu baris di JS frontend = token
   publik.
2. **Satu replika.** Jatah per IP di memori; dua replika = dua hitungan berbeda.
3. **`/api/status` membaca rantai audit**, bukan state plan. Kalau rantai
   di-reset, plan yang sudah disetujui tampak PROPOSED lagi.
4. **Batas 5 review/jam per IP** bisa terasa ketat saat uji sendiri. Naikkan
   sementara di `server/index.js` (`BATAS.run.maks`).
