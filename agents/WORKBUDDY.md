# Menjalankan loop dengan WorkBuddy sebagai modelnya

WorkBuddy tidak menerbitkan API key. Jadi jalurnya bukan HTTP, melainkan
**percakapan + berkas**: skrip mencetak prompt, model WorkBuddy menjawab,
jawabannya disimpan, lalu Reviewer deterministik menilainya.

Yang tetap sama seperti pipeline otomatis: Reviewer tidak berubah, penolakan tetap
mengutip aturan, dan setiap langkah tetap masuk audit chain.

## Lima perintah

```bash
cd "C:/.Hackathon Project"

python -m agents.workbuddy start AY-SR-101 tiktok     # sesi + prompt Planner
python -m agents.workbuddy save plan  <berkas.json>   # simpan rencana (validasi kontrak)
python -m agents.workbuddy next                       # prompt berikutnya (Writer / lapis-2)
python -m agents.workbuddy save draft <berkas.md>     # simpan draf -> lapis-1
python -m agents.workbuddy save findings <berkas>     # penilaian lapis-2 -> verdict final
```

`skip` melewati lapis-2 (tercatat sebagai `layer2_skipped` di audit log).
Tambahan: `status`, `reset` (audit log tidak dihapus).

Satu putaran review jadi **dua langkah** karena Reviewer punya dua lapis: kode dulu
(pasti dan murah), lalu model (untuk yang butuh pemahaman bahasa).

## Alur percakapan yang sebenarnya terjadi

1. `start` mencetak **prompt sistem** dan **prompt pengguna** untuk Planner.
2. Tempel keduanya ke WorkBuddy (atau minta agent WorkBuddy mengerjakannya).
   Jawabannya berupa JSON rencana.
3. Simpan JSON itu ke berkas → `save plan`. Rencana divalidasi; kalau bentuknya
   salah, ia ditolak **sebelum** masuk pipeline.
4. `next` mencetak prompt Writer. Pada iterasi ≥ 2, prompt itu sudah memuat
   catatan Reviewer (`rule_id`, kutipan, alasan, saran perbaikan).
5. Simpan jawaban model sebagai teks biasa → `save draft`. Lapis-1 langsung jalan dan
   hasilnya dicetak.
6. `next` sekarang mencetak **prompt lapis-2** (draf + lembar produk + nada merek).
   Jawabannya `{"findings": [...]}` dengan `span` disalin persis dari draf.
7. Simpan ke berkas → `save findings`. Penjaga menyaring, lalu verdict final dihitung
   dari lapis-1 + lapis-2.
8. Ulangi 4–7 sampai `LOLOS` atau tiga iterasi habis (`ESKALASI`).

Saat LOLOS, konten final ditulis ke `agents/.wb/konten-final.md` dan approval
dicatat di audit chain.

## Hasil dua percobaan nyata

**Percobaan 1 — draf dari Writer yang patuh.**

```
iterasi 1: LOLOS · 0 temuan → TERBIT (PLAN-582E57FC)
```

Model yang diberi prompt Writer (tanpa rulebook, hanya fakta boleh/dilarang)
langsung menghasilkan draf yang lolos. Ini hasil yang benar, bukan kegagalan —
tapi artinya siklus tolak→perbaiki tidak terlihat. Nilai loop baru muncul pada
draf yang datang dari luar.

**Percobaan 2 — draf agensi, dinilai dua lapis.**

Brief sengaja memuat pesan yang berbahaya; draf agensi memakainya semua.

```
iterasi 1: TOLAK · 8 temuan
  lapis-1 (kode)
    R-03  "Sudah halal, tinggal nunggu sertifikatnya keluar."
    R-07  "Hasilnya kelihatan dalam 7 hari"
    R-14  "Aman untuk semua jenis kulit" (×2)
    R-06  "Promo peluncuran Rp149.000" — padahal promo resmi Rp129.000
    R-09  klaim pencerahan tanpa disclaimer
  lapis-2 (model)
    R-04  "bekas jerawat memudar" — klaim tidak ada di lembar produk
    R-10  "Buruan sebelum habis!" — FOMO agresif, tidak ada dasarnya di brief

iterasi 2: LOLOS · 0 temuan (lapis-2 juga 0) → TERBIT (PLAN-20BF2C59)
```

Perhatikan dua hal dari hasil ini:

- **Lapis-2 menambah, bukan mengulang.** Kedua temuannya tidak akan pernah muncul dari
  kode: "bekas jerawat memudar" tidak ada di daftar kata, dan "Buruan sebelum habis"
  hanya bisa dinilai dengan memahami nada.
- **Lapis-2 tidak menolak berlebihan.** Pada iterasi 2 ia mengembalikan nol temuan untuk
  draf yang memang bersih. Model yang selalu menemukan pelanggaran sama tidak bergunanya
  dengan model yang tidak menemukan apa pun.

Enam temuan itu semuanya berasal dari pesan yang **ditandai ❌ di brief**. Artinya
alat ini menangkap persis hal yang paling mungkin lolos di tim marketing nyata.

## Yang dibuktikan, dan yang belum

**Terbukti:**

- Loop berjalan dengan model WorkBuddy, tanpa API key.
- Kontrak tetap ditegakkan: rencana/draf berbentuk salah ditolak sebelum pipeline.
- Reviewer tetap deterministik dan tetap mengutip aturan.
- Approval manusia tetap tercatat (`workbuddy-agent` propose → `EMP-014` approve →
  `execute`), dan rantai audit utuh (509 entri).

**Belum:**

- **Lapis-2 sudah jalan, tapi baru diuji dengan draf contoh.** Ia menangkap R-04 dan
  R-10 di percobaan 2 — dua hal yang tidak mungkin ditangkap kode. Yang belum: mengukur
  seberapa sering ia **melewatkan** hal berisiko. Itu butuh 10–20 draf nyata dari tim
  marketing, bukan draf yang saya tulis sendiri.
- **Ini bukan otomatisasi penuh.** Tiap langkah butuh satu balasan model. Untuk
  demo dan submission itu cukup; untuk 100 konten/hari, pakai jalur API
  (`agents/llm/client.py`) yang memakai `Layer2` yang sama.

## Satu celah yang ketemu saat percobaan ini

Draf percobaan 1 memuat frasa **"dua bahan yang paling banyak diteliti"** dan lolos
lapis-1.

Itu bukan bug kode, tapi batas desain: R-07 di rulebook adalah **daftar kata**
("terbaik", "nomor 1", "dijamin", …), bukan konsep superlatif. "Paling banyak
diteliti" tidak ada di daftar, jadi tidak tertangkap — padahal klaim itu tidak bisa
diverifikasi dari lembar produk.

Sekarang ini ditangani lapis-2, dan sudah diuji: `L-01` membuktikan lapis-1
meloloskannya, `L-03` membuktikan lapis-2 mengubah verdict jadi TOLAK.

Kenapa tidak sekadar menambah `\bpaling\b` ke daftar kata: itu akan menolak kalimat
wajar seperti "paling lama dipakai pagi". Daftar kata yang terus dipanjangkan akan
makin tidak presisi, dan presisi itulah alasan lapis-1 ada.
