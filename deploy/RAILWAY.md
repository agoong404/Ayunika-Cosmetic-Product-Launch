# Deploy — Railway

Tujuan: server MCP hidup di URL HTTPS publik, laptop boleh mati. Ini "Opsi 1"
dari `README.md`, tanpa perlu mengurus VPS/nginx/certbot sendiri.

Repo: `agoong404/Ayunika-Cosmetic-Product-Launch` (publik).

---

## 0. Sebelum mulai

Pastikan commit terakhir sudah ter-push — Railway membangun dari GitHub, bukan
dari mesin lokal:

```bash
git push origin main
```

---

## 1. Buat project

1. Railway → **New Project** → **Deploy from GitHub repo**.
2. Pilih `Ayunika-Cosmetic-Product-Launch`. Kalau repo tidak muncul, pasang
   Railway GitHub App untuk akun itu dulu.

## 2. Arahkan ke Dockerfile — jangan dilewat

Railway mencari `Dockerfile` di root repo. Dockerfile kita ada di
`deploy/Dockerfile`, jadi tanpa langkah ini Railway akan menebak (Nixpacks) dan
gagal.

**Service → Settings → Build → Dockerfile Path:** `deploy/Dockerfile`
Build context tetap root repo — semua `COPY` di Dockerfile mengasumsikan itu.

## 3. Isi variables

**Service → Variables.** Jangan taruh satu pun nilai ini di repo.

| Variable | Nilai |
|---|---|
| `MCP_TOKEN` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `MCP_APPROVER_KEYS` | JSON dari `python -m mcp_server.gen_approver_keys Nama` |
| `MCP_ALLOWED_HOSTS` | diisi di langkah 5 (butuh domain dulu) |

Buat kunci approver di mesin lokal, **bukan** di Railway:

```bash
python -m mcp_server.gen_approver_keys Agung
```

Simpan kunci aslinya untuk manusianya; yang ditempel ke `MCP_APPROVER_KEYS`
hanya bagian sha256 (`{"Agung":"<sha256>"}`). Server tidak pernah menyimpan
kunci asli.

## 4. Volume untuk rantai audit

**Service → Settings → Volumes → Add Volume**, mount path:

```
/app/engine/.audit
```

Tanpa volume, rantai hash kembali kosong setiap deploy dan `audit_verify`
kehilangan maknanya. `deploy/entrypoint.sh` menyesuaikan pemilik folder ini
karena volume ter-mount sebagai root sementara server berjalan sebagai `ayunika`.

## 5. Domain, lalu kunci host

1. **Settings → Networking → Generate Domain** → salin `xxx.up.railway.app`.
2. Set `MCP_ALLOWED_HOSTS` = hostname itu **tanpa** `https://` dan tanpa `/`.
3. Redeploy.

Tanpa ini setiap permintaan dibalas **421 Misdirected Request**, dan
pemeriksaan host berjalan sebelum kode tool — tidak akan muncul di log tool.

## 6. Verifikasi

```bash
curl -i https://HOST/health        # 200
curl -i https://HOST/mcp           # 401  (tanpa token)
curl -i -X POST https://HOST/mcp \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'   # 200
```

## 7. Daftarkan ke WorkBuddy

Tambah entri **kedua** di `~/.workbuddy-ai/mcp.json` — jangan hapus `lolos`
yang stdio:

```json
"lolos-remote": {
  "type": "streamableHttp",
  "url": "https://HOST/mcp",
  "headers": { "Authorization": "Bearer ISI_TOKEN" },
  "timeout": 30000
}
```

Mulai percakapan baru, lalu ulangi tiga pertanyaan verifikasi
(`list_products`, `review_draft`, `request_approval`).

---

## Jebakan yang sudah terbukti

1. **Domain membalas 502.** Port tidak nyambung. Image mendengarkan `8000`
   (`EXPOSE 8000`); biasanya terdeteksi otomatis. Kalau tidak, set
   `MCP_PORT=${{PORT}}` lalu redeploy, atau set target port service ke 8000.
2. **421 Misdirected Request.** `MCP_ALLOWED_HOSTS` belum memuat hostname
   Railway, atau masih ada `https://` / garis miring di nilainya.
3. **Jangan naikkan replika.** `ApprovalGate` hidup di memori dan `AuditLog`
   satu penulis. Dua replika = dua gerbang dan dua penulis pada satu rantai.
4. **Restart mengosongkan plan PROPOSED.** Volume menyelamatkan rantai audit,
   bukan gerbang di memori. Jangan rotate kunci saat ada plan menunggu.
5. **`MCP_APPROVAL_KEY` tidak boleh ikut ke Railway** kalau sudah pakai
   `MCP_APPROVER_KEYS`. Kunci asli tidak pernah ada di server.
6. **`MCP_FORWARDED_ALLOW_IPS`** default `127.0.0.1`; di belakang proxy Railway
   IP klien tercatat sebagai IP proxy. Hanya memengaruhi log, bukan routing.
