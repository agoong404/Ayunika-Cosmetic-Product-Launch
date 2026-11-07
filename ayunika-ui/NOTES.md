# Lolos — UI/UX internal (catatan untuk Claude Code)

> **Status:** internal, **belum** di-merge ke repo GitHub.
> Dibuat 7 Nov 2026. Tidak menyentuh `agoong404/Ayunika-Cosmetic-Product-Launch`.
> Tujuan: menyempurnakan tampilan `web-service` agar selaras dengan repo +
> menonjolkan yang dinilai juri Challenge C (orkestrasi 4 agent, siklus
> tolak→perbaiki→setujui, gerbang approval, audit).

---

## 1. Apa ini

SPA statis (hash-routing, tanpa framework, tanpa dependensi) yang **menggantikan
isi `web/public/`** di repo. Backend BFF (`web/server/`) **tidak diubah** —
UI ini memakai endpoint yang sudah ada.

Empat halaman:

| Route | Berkas view | Isi |
|---|---|---|
| `#/` | `viewBeranda()` | Hero, alur 5 langkah, 3 verdict, preview tim, gerbang approval |
| `#/agents` | `viewAgents()` | 4 kartu agent |
| `#/agents/:id` | `viewProfile()` | Profil Rani/Bima/Citra/Dimas (kapabilitas, batasan, tool) |
| `#/console` | `viewConsole()` | Relay 4 agent + siklus + gerbang approval |
| `#/audit` | `viewAudit()` | Tabel audit (butuh 1 endpoint baru, lihat §5) |

## 2. Struktur berkas

```
public/
  index.html          # shell + navigasi + mount #app
  styles.css          # 1 file; token warna + dark mode (prefers-color-scheme + [data-theme])
  app.js              # router hash + semua view + pemanggilan /api/*
  data/agents.js      # profil 4 agent — STATIS, sumber: expert/.../agents/*.md
  data/demo.js        # replay siklus tolak→perbaiki→setujui (contoh terekam)
  assets/avatars/     # bima/citra/dimas/rani/team.png — disalin dari expert/.../avatars/
```

## 3. Cara pindah ke repo (lewat Claude Code, saat sudah siap merge)

1. Salin isi `public/` ini ke `web/public/` di repo (menimpa `index.html`,
   `styles.css`, `app.js`; menambah `data/` dan `assets/avatars/`).
2. Avatar berasal dari `expert/ayunika-compliance-team/avatars/` — boleh
   di-`git mv`/symlink atau biarkan tersalin di `web/public/assets/avatars/`.
3. BFF `web/server/index.js` **tidak perlu diubah** untuk 4 halaman utama.
   Hanya halaman `#/audit` yang butuh 1 endpoint baru (§5).
4. Jalankan lokal: `cd web && MCP_URL=... MCP_TOKEN=... node server/index.js`
   → buka `http://localhost:8080`. Hash-routing bekerja tanpa ubahan
   `layaniStatis` (server hanya melihat `/`, aset diambil per path).
5. Perbarui `submission_templates/07_submission_checklist.md` item 11 & baris
   UX (situs sudah live + UI baru) begitu di-deploy.

## 4. Endpoint yang dipakai (sudah ada di BFF)

| UI | Endpoint | Tool MCP di balik |
|---|---|---|
| dropdown SKU | `GET /api/products` | `list_products` |
| tombol sudut | `GET /api/sudut` | (daftar lokal BFF) |
| Jalankan review | `POST /api/run` {sku, platform, angle?} | `run_cycle` |
| Ajukan approval | `POST /api/propose` {sku, platform, content} | `request_approval` |
| Status plan | `GET /api/status?plan_id=` | `audit_tail` |
| teks aturan | `POST /api/rulebook` {ids} | `get_rulebook` |

Prinsip yang DIPERTAHANKAN: **tidak ada tombol setuju di situs**. `#/console`
hanya `request_approval` (PROPOSED) lalu polling status. `approve_publication`
tetap hanya lewat kunci approver manusia.

## 5. Satu endpoint baru (opsional, hanya untuk halaman #/audit)

Halaman Audit butuh `GET /api/audit?n=20` yang memanggil tool `audit_tail` dan
mengembalikan `{ entri: [...] }`. Tambahkan di `web/server/index.js` di dalam
`tanganiApi`:

```js
if (req.method === "GET" && url.pathname === "/api/audit") {
  const n = Math.min(Number(url.searchParams.get("n")) || 20, 100);
  return kirim(res, 200, await klien.panggilTool("audit_tail", { n }));
}
```

`audit_tail` sudah termasuk 5 tool yang diizinkan publik, jadi ini tidak
melanggar batas "situs hanya menjangkau 5 tool". Sampai endpoint ini ada,
halaman Audit menampilkan panduan, bukan data karangan.

## 6. Keputusan desain yang penting

- **Relay, bukan satu kotak.** SOP Rani (`ayunika-team-lead.md`) melarang
  `run_cycle` karena "meleburkan tiga peran jadi satu dan membuat anggota
  sekadar hiasan". UI menampilkan fase per-agent (Rani→Bima→Citra→Dimas) agar
  orkestrasi terlihat. Catatan: BFF publik tetap memakai `run_cycle` (jalur
  tanpa-LLM); timeline memetakan `riwayat` yang dikembalikannya ke tiap agent.
  **Peningkatan berikutnya:** ekspос rantai granular (`plan_content`,
  `write_draft`, `review_draft`) ke BFF agar relay menampilkan teks draf tiap
  iterasi dari hasil live, bukan hanya verdict.
- **Mode replay (`data/demo.js`).** Writer deterministik "konservatif" → hampir
  selalu LOLOS di iterasi 1, jadi siklus jarang terlihat live. Tombol "Putar
  contoh tolak→perbaiki→setujui" memutar siklus utuh dari pola DRAFT-101,
  **ditandai jelas sebagai contoh terekam**. Ganti isinya bila pakai kasus lain.
- **Profil agent statis.** `data/agents.js` disalin dari front-matter + bagian
  "Core capabilities"/"Boundary rules" tiap `.md`. **Bila file .md berubah,
  perbarui `agents.js`** — jangan mengarang kapabilitas baru.
- **Dark mode** via `prefers-color-scheme` + override `[data-theme]`. Warna
  verdict (ok/no/wait) dipertahankan dari `styles.css` lama agar konsisten.

## 7. Pemetaan ke rubrik juri (10×10)

| Elemen UI | Dimensi |
|---|---|
| Relay 4 agent + badge iterasi | AI Interaction (agentic, bukan pass-through) |
| Kartu v1→v2→v3 + temuan R-xx | Demo & Storytelling · syarat wajib siklus |
| Profil + kapabilitas/batasan | Human-Centered Design (pemisahan tugas) |
| Gerbang approval tanpa tombol setuju | Responsible AI & Ethics |
| Halaman Audit (hash chain) | Responsible AI & Ethics (Record) |
| Nama ID/中文 | Innovation · UX & Accessibility |

## 8. TODO sebelum merge

- [ ] Review tampilan di device nyata (sudah diuji responsif 1 kolom < 760px).
- [ ] Tambah `GET /api/audit` (§5) bila halaman Audit mau tayang data live.
- [ ] (Opsional kuat) ekspos rantai granular agar relay live menampilkan draf
      tiap iterasi + memicu TOLAK alami, bukan hanya replay.
- [ ] Sinkronkan `agents.js` bila `expert/.../agents/*.md` berubah.
- [ ] Perbarui checklist submission item 11 + baris UX.
- [ ] Hapus `preview-server.js` & `shot.mjs` saat merge — itu hanya alat
      pratinjau lokal, bukan bagian situs.

## 9. Pratinjau lokal (internal, tanpa MCP)

`preview-server.js` menyajikan `public/` dan memalsukan `/api/*` dengan data
contoh — hanya untuk melihat tampilan. **Bukan untuk deploy.**

```
node preview-server.js   # http://localhost:8099
```
