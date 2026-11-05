"""
__main__.py — jalankan server HTTP (Path B).

    $env:MCP_TOKEN = "..."          # wajib
    $env:MCP_APPROVAL_KEY = "..."   # wajib untuk gerbang approval
    $env:MCP_ALLOWED_HOSTS = "mcp.contoh.com"
    .\\.venv\\Scripts\\python.exe -m mcp_server

Kenapa `workers=1` bukan saran tapi syarat: `ApprovalGate` menyimpan plan di
memori proses, dan `AuditLog` mengasumsikan satu penulis. Dua worker berarti dua
gerbang terpisah dan dua penulis pada satu rantai hash.
"""
from __future__ import annotations

import os
import sys

import uvicorn


def main() -> int:
    token = os.environ.get("MCP_TOKEN", "").strip()
    if not token:
        print("MCP_TOKEN wajib diisi. Tanpa itu server menolak semua permintaan /mcp.",
              file=sys.stderr)
        print("Contoh: $env:MCP_TOKEN = \"$(...acak...)\"", file=sys.stderr)
        return 2

    from mcp_server import tools as _t
    if not _t.registri_siap():
        print("PERINGATAN: tidak ada registri approver yang sah. approve_publication "
              "akan menolak semua permintaan. Isi MCP_APPROVER_KEYS (JSON "
              '{"Nama": "<sha256(kunci)>"}) atau MCP_APPROVAL_KEY + '
              "MCP_APPROVAL_KEY_OWNER. Buat kunci per manusia: "
              "python -m mcp_server.gen_approver_keys Nama", file=sys.stderr)

    if not os.environ.get("MCP_ALLOWED_HOSTS", "").strip():
        print("PERINGATAN: MCP_ALLOWED_HOSTS kosong. Hanya host lokal yang diterima; "
              "permintaan dari domain publik akan dibalas 421.", file=sys.stderr)

    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8000"))
    print(f"lolos-mcp mendengarkan di http://{host}:{port}/mcp "
          f"(health: /health)", file=sys.stderr)

    uvicorn.run(
        "mcp_server.http:app",
        host=host,
        port=port,
        workers=1,
        proxy_headers=True,
        forwarded_allow_ips=os.environ.get("MCP_FORWARDED_ALLOW_IPS", "127.0.0.1"),
        log_level=os.environ.get("MCP_LOG_LEVEL", "info"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
