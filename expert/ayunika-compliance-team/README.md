# Ayunika Compliance Team — paket expert WorkBuddy

Empat agent yang membuat konten peluncuran kosmetik **lolos aturan sebelum terbit**,
dengan satu mesin di belakang: MCP service Lolos yang sudah live.

```
Pengguna → Rani (lead) → Bima (plan) → Citra (draft) → Dimas (review)
                                        ↑                │
                                        └── temuan ──────┘  (maks 3 iterasi)
                          Rani → request_approval → PROPOSED (kunci manusia)
```

## Isi

| Berkas | Peran |
|---|---|
| `.codebuddy-plugin/plugin.json` | Kartu tim: `expertType: team`, 4 anggota, 3 tags, 3 quick prompts, `teamInfo`, `members[]` |
| `settings.json` | `{"agent": "ayunika-team-lead"}` — wajib untuk team |
| `agents/ayunika-team-lead.md` | Rani: orkestrasi, batas iterasi, laporan akhir |
| `agents/ayunika-planner.md` | Bima: fakta & struktur per platform |
| `agents/ayunika-writer.md` | Citra: naskah per platform |
| `agents/ayunika-reviewer.md` | Dimas: verdict + temuan berisi kutipan |
| `avatars/*.png` | Kartu tim + 4 avatar anggota (hasil generate) |
| `../build.py` | Generator avatar + pemasang |

## Tiga peran + satu lead

| Agent ID | Nama | Peran | Tool MCP yang dipakai |
|---|---|---|---|
| `ayunika-team-lead` | Rani | Orkestrasi, iterasi, laporan | `list_products`, `request_approval`, `audit_verify` |
| `ayunika-planner` | Bima | Facts & struktur per platform | `get_context`, `get_rulebook`, `plan_content` |
| `ayunika-writer` | Citra | Naskah per platform | `write_draft` |
| `ayunika-reviewer` | Dimas | Verdict + temuan | `review_draft` |

Tiap anggota adalah konteks terpisah. Itulah inti desainnya: **Writer tidak pernah
melihat rulebook**, hanya Reviewer yang boleh. Kalau penulis tahu daftar kata
terlarang, ia akan menghindarinya tanpa memahami maksudnya, dan siklus
tolak → perbaiki berhenti terjadi.

## Empat kriteria brief

| Kriteria brief | Bagaimana dipenuhi |
|---|---|
| Menghasilkan konten untuk beberapa platform | Satu rencana dan satu naskah per platform (`tiktok`, `instagram`, `marketplace`) |
| Menolak output yang melanggar aturan | `review_draft` → `TOLAK`, dit Deterministik oleh `engine/reviewer.py` |
| Menpjelaskan dasar penolakan | Tiap temuan: `rule_id` + `span` kutipan persis + `reason` + `fix` |
| Memperbaiki sampai lolos | `write_draft` dengan `feedback`, maks 3 iterasi, lalu `ESKALASI` |

## Skill: dibatalkan di dalam paket

Paket ini **tidak** mendeklarasikan `skills`. Batas peran tiap anggota sudah
tertulis di agent MD masing-masing, dan eksekusi lewat MCP. Menyalin `SKILL.md`
lagi ke dalam paket hanya menciptakan sumber kebenaran kelima yang bisa
simpang — masalah yang sudah pernah terjadi pada teks aturan R-01..R-15.

`skills/` tetap ada di repo sebagai jalur pemakaian mandiri (tanpa expert).

## Yang tidak boleh dilanggar

- `approve_publication` tidak pernah dipanggil. Rantai berhenti di `PROPOSED`.
- `run_cycle` tidak dipakai di mode tim: ia menjalankan ketiga peran dalam satu
  panggilan dan membuat anggota tim jadi dekoratif.
- Tanpa `mcp__lolos__*`, expert wajib berkata "Saya tidak bisa memverifikasi",
  bukan menilai dengan prosa.

## Pasang

```bash
python expert/build.py            # generate + cek struktur
python expert/build.py --pasang   # + salin ke my-experts + validate + register
```

`--pasang` memakai `WORKBUDDY_CONFIG_DIR` bila diset; pada mesin ini nilainya
`C:/Users/Agung Wahyu Kusuma/.workbuddy-ai`. Setelahnya **mulai ulang
WorkBuddy**, lalu buka **Experts → My Experts**.

## Batas yang diakui

- **Belum dipublikasikan** ke Expert Center. Paket ini lokal (`my-experts`),
  jadi tidak punya `sharecode` / tautan bagikan publik — kode itu diterbitkan
  server saat pengajuan Marketplace disetujui.
- **Bergantung pada MCP service.** Tanpa tool, team wajib menyatakan tidak
  bisa memverifikasi.
- Kapabilitas bonus (kartu gambar + OCR, kamus fakta tiga bahasa, usulan
  aturan) tersedia sebagai tool terpisah dan tidak pernah melewati gerbang
  approval. Batas lengkap ada di `agents/ayunika-team-lead.md`.
