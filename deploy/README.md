# Deploy — Path B (server publik)

> **Paling cepat:** [`RAILWAY.md`](RAILWAY.md) — deploy dari GitHub tanpa VPS,
> nginx, atau certbot. Berkas di folder ini dipakai kalau memilih VPS/Docker.

Path A (`stdio`) hanya bekerja bila proses berjalan di mesin yang sama dengan
WorkBuddy. Untuk "repo ini jadi situs", server harus punya URL HTTPS publik.

Tiga berkas di folder ini:

| Berkas | Untuk |
|---|---|
| `ayunika-care-mcp.service` | systemd, VPS/Cloud |
| `nginx-ayunika-care-mcp.conf` | reverse proxy + TLS |
| `Dockerfile` | host berbasis kontainer |

---

## Sebelum apa pun: buktikan dulu secara lokal

```powershell
$env:MCP_TOKEN = "token-lokal-panjang"
# Satu kunci per manusia; server hanya menyimpan sha256-nya.
$env:MCP_APPROVER_KEYS = '{"Agung":"<sha256-dari-gen_approver_keys>"}'
$env:MCP_ALLOWED_HOSTS = ""
.\\.venv\\Scripts\\python.exe -m mcp_server.test_http
```

Kalau ini lulus, masalah berikutnya pasti di DNS/TLS/nginx, bukan di kode.

---

## Opsi 1 — VPS Ubuntu 24.04

**DNS:** `mcp.contoh.com` → IP instance. Buka port 80 dan 443.

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv nginx certbot python3-certbot-nginx git
sudo useradd -m -s /bin/bash ayunika
sudo -u ayunika git clone <repo> /home/ayunika/app
cd /home/ayunika/app
sudo -u ayunika python3.12 -m venv .venv
sudo -u ayunika .venv/bin/pip install -r requirements-mcp.txt
```

Buat dua kunci (jangan pakai contoh):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Isi ke `deploy/ayunika-care-mcp.service`, lalu:

```bash
sudo cp deploy/ayunika-care-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ayunika-care-mcp
curl http://127.0.0.1:8000/health
```

nginx:

```bash
sudo cp deploy/nginx-ayunika-care-mcp.conf /etc/nginx/sites-available/ayunika-care-mcp
sudo sed -i 's/mcp.contoh.com/mcp.DOMAIN-ANDA.com/' /etc/nginx/sites-available/ayunika-care-mcp
sudo ln -s /etc/nginx/sites-available/ayunika-care-mcp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d mcp.DOMAIN-ANDA.com
```

Verifikasi:

```bash
curl -i https://mcp.DOMAIN-ANDA.com/health          # 200
curl -i https://mcp.DOMAIN-ANDA.com/mcp             # 401
curl -i -X POST https://mcp.DOMAIN-ANDA.com/mcp \
  -H "Authorization: Bearer <MCP_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'   # 200
```

`421 Misdirected Request` berarti `MCP_ALLOWED_HOSTS` tidak memuat domain itu.
Pemeriksaan ini berjalan sebelum kode tool, jadi tidak akan muncul di log tool.

---

## Opsi 2 — Cloudflare Tunnel (demo tanpa domain)

Cocok untuk demo hackathon. Tetap HTTPS, tidak perlu buka port.

```powershell
# terminal 1
$env:MCP_TOKEN = "token-demo"
# Kunci per manusia: python -m mcp_server.gen_approver_keys Agung
$env:MCP_APPROVER_KEYS = '{"Agung":"<sha256>"}'
$env:MCP_ALLOWED_HOSTS = ""      # diisi setelah URL tunnel keluar
.\\.venv\\Scripts\\python.exe -m mcp_server

# terminal 2
cloudflared tunnel --url http://127.0.0.1:8000
```

`cloudflared` mencetak URL seperti `https://acak-acak.trycloudflare.com`. URL
itu berubah setiap kali tunnel dijalankan ulang, dan harus dimasukkan ke
`MCP_ALLOWED_HOSTS` (tanpa `https://`) lalu server dijalankan ulang.

---

## Opsi 3 — Docker

```bash
docker build -f deploy/Dockerfile -t ayunika-care-mcp .
docker run -p 8000:8000 \
  -e MCP_TOKEN="$MCP_TOKEN" \
  -e MCP_APPROVER_KEYS="$MCP_APPROVER_KEYS" \
  -e MCP_ALLOWED_HOSTS="mcp.contoh.com" \
  -v ayunika-care-audit:/app/engine/.audit \
  ayunika-care-mcp
```

Atau tanpa env: mount JSON registri ke `/app/.approver_keys`
(`-v "$PWD/.approver_keys:/app/.approver_keys:ro"`).

---

## Mendaftarkan ke WorkBuddy

Setelah URL hidup, tambahkan entri **kedua** di
`~/.workbuddy-ai/mcp.json` (jangan hapus entri `lolos` yang stdio):

```json
{
  "mcpServers": {
    "lolos-remote": {
      "type": "streamableHttp",
      "url": "https://mcp.contoh.com/mcp",
      "headers": {
        "Authorization": "Bearer ISI_TOKEN_DI_SINI"
      },
      "timeout": 30000
    }
  }
}
```

Lalu mulai percakapan baru di WorkBuddy dan ulangi tiga pertanyaan verifikasi.

---

## Yang tidak boleh dilakukan

1. **Jangan jalankan lebih dari satu worker.** `ApprovalGate` di memori,
   `AuditLog` satu penulis. `workers=1` di service dan Dockerfile sudah benar.
2. **Jangan matikan `MCP_ALLOWED_HOSTS`.** Itu satu-satunya yang menahan DNS
   rebinding.
3. **Jangan hapus `proxy_buffering off`.** Tanpa itu stream menggantung.
4. **Jangan simpan `MCP_TOKEN` di repo atau di `connector-meta.json`.**
5. **Jangan taruh kunci approval di mesin yang sama dengan agen.** Kunci per
   approver disimpan sebagai **sha256** di `MCP_APPROVER_KEYS` atau
   `.approver_keys` — kunci asli tinggal di tangan manusianya. Di VPS, agen
   tidak bisa membaca berkas server; di lokal, bisa — dan kunci yang bisa
   dibaca agen membuat gerbang approval menjadi formalitas. Nama approver
   diturunkan dari kunci, jadi agen tidak bisa mengaku manusia mana pun.
