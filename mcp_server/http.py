"""
http.py — transport Streamable HTTP di `/mcp`, plus `/health` dan pemeriksaan token.

Dipakai hanya untuk Path B (server publik). Path A memakai `stdio.py`.

Yang dijaga berkas ini, dan alasannya:

  · Token bearer diperiksa SEBELUM permintaan mencapai kode MCP. Tanpa ini, siapa
    pun yang menemukan URL bisa menjalankan tool dan membaca registri produk.
  · Middleware ditulis sebagai ASGI mentah, bukan `BaseHTTPMiddleware`. Yang
    terakhir menyangga respons dan memutus stream SSE — gejalanya "koneksi
    menggantung", bukan error yang jelas.
  · `MCP_ALLOWED_HOSTS` wajib diisi di produksi. Tanpa itu setiap permintaan
    dibalas 421 Misdirected Request, dan pemeriksaan itu berjalan sebelum kode
    tool, jadi tidak akan terlihat di log tool.
  · `/health` sengaja terbuka supaya monitor dan load balancer bisa memeriksa
    proses tanpa memegang token. Isinya tidak menyebut apa pun tentang data.
"""
from __future__ import annotations

import hmac
import logging
import os

from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from .server import mcp

log = logging.getLogger("lolos.mcp.http")

# Host lokal selalu diizinkan: itu yang dipakai saat menguji sebelum deploy.
_HOST_LOKAL = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*",
               "[::1]", "[::1]:*"]


def _host_diizinkan() -> list[str]:
    """Host lokal + MCP_ALLOWED_HOSTS (dipisah koma)."""
    tambahan = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",")
                if h.strip()]
    hasil = list(_HOST_LOKAL)
    for h in tambahan:
        hasil.append(h)
        if not h.endswith(":*") and h.count(":") == 0:
            hasil.append(f"{h}:*")      # sembarang port
    return list(dict.fromkeys(hasil))


def _origin_diizinkan(hosts: list[str]) -> list[str]:
    """Origin untuk klien berbasis browser. Klien desktop tidak mengirim Origin."""
    hasil = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    for h in hosts:
        if h.startswith(("127.0.0.1", "localhost", "[::1]")):
            continue
        dasar = h[:-2] if h.endswith(":*") else h
        hasil.append(f"https://{dasar}")
        hasil.append(f"https://{dasar}:*")
    return list(dict.fromkeys(hasil))


class AuthMiddleware:
    """Bearer token untuk semua jalur kecuali `/health`. ASGI mentah, tanpa buffer."""

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope.get("path") == "/health":
            return await self.app(scope, receive, send)

        header = dict(scope.get("headers") or [])
        auth = header.get(b"authorization", b"").decode("latin-1")
        harapan = f"Bearer {self.token}"
        cocok = bool(self.token) and hmac.compare_digest(
            auth.encode("latin-1"), harapan.encode("latin-1"))
        if not cocok:
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"application/json"),
                            (b"www-authenticate", b'Bearer realm="lolos"')],
            })
            await send({"type": "http.response.body",
                        "body": b'{"error":"invalid_token"}'})
            return
        return await self.app(scope, receive, send)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    return JSONResponse({"status": "ok", "service": "lolos-mcp"})


def build_app():
    """Bangun aplikasi ASGI. Dipanggil sekali saat modul diimpor."""
    hosts = _host_diizinkan()
    keamanan = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=_origin_diizinkan(hosts),
    )
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,       # tidak ada callback ke klien; sesi hanya menambah state
        transport_security=keamanan,
    )
    token = os.environ.get("MCP_TOKEN", "").strip()
    if not token:
        # Fail-closed: tanpa token, setiap permintaan /mcp ditolak 401.
        log.warning("MCP_TOKEN kosong — semua permintaan /mcp akan ditolak 401.")
    return AuthMiddleware(app, token=token)


app = build_app()
