"""
test_http.py — uji transport Streamable HTTP dengan server sungguhan.

Menjalankan `python -m mcp_server` sebagai proses terpisah, lalu memeriksa:
  · /health terbuka tanpa token
  · /mcp menolak 401 tanpa token dan dengan token salah
  · Host yang tidak diizinkan dibalas 421
  · klien SDK MCP benar-benar bisa list_tools dan call_tool

Pemakaian:
    .venv\\Scripts\\python.exe -m mcp_server.test_http
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import anyio
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="lolos-mcp-http-"))
TOKEN = "token-uji-http-jangan-dipakai"
KUNCI = "kunci-uji-http-jangan-dipakai"

GAGAL: list[str] = []


def cek(nama: str, kondisi: bool, detail: object = "") -> None:
    print(f"  {'ok   ' if kondisi else 'GAGAL'} {nama}" + (f"  {detail}" if not kondisi else ""))
    if not kondisi:
        GAGAL.append(nama)


def _port_bebas() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


PORT = _port_bebas()
BASE = f"http://127.0.0.1:{PORT}"
MCP = f"{BASE}/mcp"


def _tunggu_siap(batas: float = 30.0) -> bool:
    akhir = time.time() + batas
    while time.time() < akhir:
        try:
            if httpx2.get(f"{BASE}/health", timeout=1.0).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


async def _uji_protokol() -> None:
    print("\n5. Klien SDK MCP lewat HTTP")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx2.AsyncClient(headers=headers, timeout=60.0) as http:
        transport = streamable_http_client(MCP, http_client=http)
        async with Client(transport) as client:
            daftar = await client.list_tools()
            nama = sorted(t.name for t in daftar.tools)
            cek("12 tool terdaftar", len(nama) == 12, f"{len(nama)}: {nama}")

            hasil = await client.call_tool("list_products", {})
            isi = hasil.structured_content
            if not isi:
                for blok in hasil.content or []:
                    if getattr(blok, "text", None):
                        import json
                        isi = json.loads(blok.text)
                        break
            cek("list_products lewat HTTP", (isi or {}).get("jumlah") == 4, isi)

            review = await client.call_tool("review_draft", {
                "draft": "Ayunika Bright Serum sudah halal dan dijamin glowing.",
                "sku": "AY-SR-101",
                "platform": "tiktok",
            })
            isi = review.structured_content
            if not isi:
                for blok in review.content or []:
                    if getattr(blok, "text", None):
                        import json
                        isi = json.loads(blok.text)
                        break
            cek("review_draft TOLAK lewat HTTP", (isi or {}).get("verdict") == "TOLAK", isi)


def main() -> int:
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "PYTHONIOENCODING": "utf-8",
        "MCP_TOKEN": TOKEN,
        "MCP_APPROVAL_KEY": KUNCI,
        "MCP_APPROVAL_KEY_OWNER": "Agung",
        "HALAL_AUDIT_DIR": str(TMP),
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": str(PORT),
        "MCP_LOG_LEVEL": "warning",
    }
    out = open(TMP / "server.out", "w", encoding="utf-8")
    err = open(TMP / "server.err", "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "mcp_server"], cwd=str(ROOT),
                            env=env, stdout=out, stderr=err)
    try:
        print(f"\n0. Menyalakan server di {BASE}")
        if not _tunggu_siap():
            print("  GAGAL server tidak siap dalam 30 detik")
            print("  --- stderr ---")
            print((TMP / "server.err").read_text(encoding="utf-8", errors="replace")[-3000:])
            return 1
        cek("server siap", True)

        print("\n1. /health")
        r = httpx2.get(f"{BASE}/health", timeout=5.0)
        cek("200 tanpa token", r.status_code == 200, r.status_code)
        cek("body menyebut ok", r.json().get("status") == "ok", r.text)

        print("\n2. /mcp tanpa token")
        r = httpx2.post(MCP, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                        timeout=5.0)
        cek("401 tanpa header", r.status_code == 401, r.status_code)
        cek("ada WWW-Authenticate", "www-authenticate" in {k.lower() for k in r.headers},
            dict(r.headers))

        print("\n3. /mcp dengan token salah")
        r = httpx2.post(MCP, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                        headers={"Authorization": "Bearer token-palsu"}, timeout=5.0)
        cek("401 token salah", r.status_code == 401, r.status_code)

        print("\n4. Host tidak diizinkan")
        r = httpx2.post(MCP, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                        headers={"Authorization": f"Bearer {TOKEN}",
                                 "Host": "evil.example.com"},
                        timeout=5.0)
        cek("421 host asing", r.status_code == 421, r.status_code)

        anyio.run(_uji_protokol)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        out.close()
        err.close()

    print("\n" + "-" * 62)
    if GAGAL:
        print(f"GAGAL {len(GAGAL)} pemeriksaan: {GAGAL}")
        print("--- stderr server ---")
        print((TMP / "server.err").read_text(encoding="utf-8", errors="replace")[-3000:])
        return 1
    print("LULUS semua pemeriksaan transport HTTP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
