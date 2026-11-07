# skills/ — tiga skill Ayunika Care

Folder ini adalah **salinan kanonik** yang ikut ke repo submission. WorkBuddy sendiri
membaca skill dari lokasi konfigurasi, bukan dari sini — lihat bagian "Satu sumber,
tiga lokasi" di bawah.

```
skills/
├── ayunika-planner/   SKILL.md + scripts/load_context.py
├── ayunika-writer/    SKILL.md + scripts/check_plan.py
└── ayunika-reviewer/  SKILL.md + scripts/review.py
```

## Rantai

```
ayunika-planner ──▶ ayunika-writer ──▶ ayunika-reviewer
                      ▲                  │
                      └───── TOLAK ──────┘   (maks 3 iterasi, lalu eskalasi)
```

| Skill | Peran | Menyerahkan ke |
|---|---|---|
| `ayunika-planner` | brief → rencana tervalidasi | `ayunika-writer` |
| `ayunika-writer` | rencana + catatan → draf | `ayunika-reviewer` |
| `ayunika-reviewer` | dua lapis → verdict | `ayunika-writer` (TOLAK) / approval (LOLOS) |

Ketiganya tersambung lewat **state sesi** (`agents/.wb/session.json`), bukan saling
memanggil langsung.

## Pasang

PowerShell:

```powershell
python skills/sync.py
```

Git Bash:

```bash
python skills/sync.py
```

Perintah itu menyalin ketiga skill ke dua lokasi yang dibaca WorkBuddy. Setelahnya,
**mulai percakapan baru** — skill dibaca saat sesi lahir, bukan saat file ditulis.

## Satu sumber, tiga lokasi

| Lokasi | Perannya | Boleh diedit? |
|---|---|---|
| `skills/` | **kanonik** — ikut repo, jadi bukti submission | ya, di sini |
| `.workbuddy-ai/skills/` | dibaca WorkBuddy untuk workspace ini | tidak — hasil salin |
| `~/.workbuddy-ai/skills/` | dibaca lintas proyek | tidak — hasil salin |

Aturannya satu: **ubah di `skills/`, lalu jalankan `python skills/sync.py`.** Kalau
mengedit di dua tempat, keduanya akan berbeda diam-diam — dan itu sudah pernah terjadi
pada teks aturan yang tertinggal di R-01..R-15.

## Batas yang perlu diketahui

Skill ini **bukan paket mandiri**. Ia memanggil `engine/` dan `dataset_c/` di repo:

- `ayunika-reviewer/scripts/review.py` mengimpor `engine/reviewer.py`
- `ayunika-planner/scripts/load_context.py` membaca `dataset_c/`
- perintah `python -m agents.workbuddy` butuh root repo sebagai direktori kerja

Artinya: skill ini bekerja di mesin yang punya repo ini. Untuk paket yang bisa dipasang
orang lain tanpa repo, `engine/` dan `dataset_c/` harus ikut dibundel — dan itu berarti
dua salinan engine yang harus dijaga tetap sama. Itu keputusan terpisah, bukan bawaan
dari folder ini.
