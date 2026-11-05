# Plan: Demo Live Link (item 11 — BONUS)

> Disimpan 31 Okt 2026, 21:05. Status: **ditunda** — prioritas tetap video demo (WAJIB).
> Eksekusi plan ini ±2–3 jam, aman dilakukan setelah video selesai direkam.

## Konteks

WorkBuddy **belum punya API key**, jadi model di dalamnya tidak bisa dipanggil
programatik dari backend (tertulis di `06_product_sharing.md` bagian kritik).
Jembatan `agents/workbuddy.py` butuh satu balasan manual per langkah — cukup untuk
video, tidak untuk server live. Konsekuensinya: demo live tidak boleh bergantung
pada model WorkBuddy sebagai base LLM.

Kabar baiknya: **inti yang dinilai juri tidak butuh LLM.** Rulebook R-01..R-21,
pemeriksaan harga/kuota/halal, gerbang approval, dan audit hash-chain semuanya kode
deterministik yang sudah teruji 1100 eksekusi.

## Opsi yang dipertimbangkan

| Opsi | Apa yang jalan | Risiko | Waktu | Keputusan |
|---|---|---|---|---|
| **A. Web demo deterministik** | Engine sungguhan di server; lapis-1 live, lapis-2 replay sesi terekam (dilabeli jujur) | Rendah | ±2–3 jam | **DIPILIH** |
| B. Provider LLM nyata via `.env` + `agents/llm/client.py` | Lapis-2 & Writer mode model hidup sungguhan | Butuh kredensial + uji ulang; hasil tak deterministik | ±1 jam + risiko | Penambah opsional |
| C. Skip demo live | — | Nol (item bonus) | 0 | Fallback kalau mepet |

## Rancangan opsi A (saat dieksekusi)

**Stack:** FastAPI (satu berkas) + satu halaman HTML, memakai `engine/` apa adanya.
Dipublikasikan lewat skill "publish as application" → link online untuk form submission.

**Alur di halaman:**

1. Pilih SKU (AY-SR-101..104) + platform (tiktok/instagram/marketplace)
2. Tombol "Jalankan siklus" → pipeline deterministik: Planner → Writer → Reviewer
   → ditampilkan per iterasi: verdict, temuan per lapis (kode vs model), kutipan, fix
3. Kolom tempel draf sendiri → Reviewer lapis-1 menilai live (ini yang paling berkesan:
   juri menempel klaim melanggar dan melihat nomor aturannya)
4. Gerbang approval: tombol "Setujui" dengan token plan_id sekali pakai
5. Panel audit: `governance.py verify` dijalankan live + tail entri terakhir

**Kejujuran yang wajib ditampilkan di halaman:**

- Lapis-2 (model) pada demo ini adalah **replay temuan dari sesi terekam**, bukan
  penilaian model live — karena WorkBuddy belum punya API programatik.
- Lapis-1, gerbang approval, dan audit chain **live sungguhan**.
- Kalau nanti `.env` terisi provider nyata, lapis-2 live menggantikan replay —
  kode `Layer2.run()` sudah siap untuk itu.

**Langkah eksekusi nanti:**

1. `engine/demo_app.py` — FastAPI: 3 endpoint (run cycle, review draft, audit verify)
2. Satu HTML + JS ringan, bahasa Indonesia, mobile-friendly
3. Uji lokal → skill publish-as-application → simpan link ke `07_submission_checklist.md`
4. Update item 11 di checklist: ⬜ → ✅ + link

## Catatan

- Jangan biarkan plan ini menggeser prioritas: **video (WAJIB) > repo publik (WAJIB) >
  demo live (BONUS)**.
- Kalau provider LLM nyata sudah terpasang, jalankan dulu `run_official_cases.py --ulang 50`
  untuk mengukur dampaknya sebelum dipamerkan live — hasil tidak lagi 50/50 identik,
  dan pergeseran itulah yang perlu dilaporkan apa adanya.
