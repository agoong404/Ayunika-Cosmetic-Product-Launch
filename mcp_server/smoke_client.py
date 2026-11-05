"""
smoke_client.py — uji protokol sungguhan lewat stdio.

Skrip ini menjalankan `python -m mcp_server.stdio` sebagai proses anak, lalu
berbicara MCP dengannya persis seperti WorkBuddy akan berbicara. Bedanya dengan
run_tests.py: di sini transport, handshake, dan serialisasi ikut diuji.

Pemakaian:
    .venv\\Scripts\\python.exe -m mcp_server.smoke_client
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="lolos-mcp-asap-"))
KUNCI = "kunci-asap-hanya-untuk-uji"
# Kunci yang tidak terdaftar — untuk membuktikan gerbang kunci tetap bekerja
# lewat protokol sungguhan, bukan hanya di unit test.
KUNCI_ASING = "kunci-asing-asap-0123456789abcdef"

PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "mcp_server.stdio"],
    cwd=str(ROOT),
    env={
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "PYTHONIOENCODING": "utf-8",
        "HALAL_AUDIT_DIR": str(TMP),
        # Satu kunci per manusia, hanya sha256-nya yang disimpan server.
        # Kasus registri berisi nama pemohon diuji di run_tests.py (ditolak
        # saat dimuat — satu entri buruk membatalkan seluruh registri).
        "MCP_APPROVER_KEYS": json.dumps({
            "Agung": hashlib.sha256(KUNCI.encode("utf-8")).hexdigest(),
        }),
    },
)

GAGAL: list[str] = []


def cek(nama: str, kondisi: bool, detail: object = "") -> None:
    print(f"  {'ok   ' if kondisi else 'GAGAL'} {nama}" + (f"  {detail}" if not kondisi else ""))
    if not kondisi:
        GAGAL.append(nama)


def _isi(hasil) -> dict:
    """Ambil payload JSON dari hasil tool.

    Tool mengembalikan `dict` tanpa model keluaran, jadi SDK mengirimnya sebagai
    teks JSON di `content[0].text`, bukan `structuredContent`. Klien MCP mana pun
    bisa membaca bentuk ini.
    """
    if hasil.structured_content:
        return hasil.structured_content
    for blok in hasil.content or []:
        teks = getattr(blok, "text", None)
        if teks:
            import json
            try:
                return json.loads(teks)
            except json.JSONDecodeError:
                return {"_teks": teks}
    return {}


async def main() -> int:
    async with Client(PARAMS) as client:
        print("\n1. Handshake & daftar tool")
        daftar = await client.list_tools()
        nama = sorted(t.name for t in daftar.tools)
        cek("12 tool terdaftar", len(nama) == 12, f"{len(nama)}: {nama}")
        for wajib in ("list_products", "review_draft", "run_cycle",
                      "request_approval", "approve_publication"):
            cek(f"tool {wajib} ada", wajib in nama)

        print("\n2. list_products")
        hasil = await client.call_tool("list_products", {})
        isi = _isi(hasil)
        cek("tidak error", hasil.is_error is not True, hasil.content)
        cek("4 SKU", isi.get("jumlah") == 4, isi.get("jumlah"))

        print("\n3. review_draft menolak klaim halal palsu")
        hasil = await client.call_tool("review_draft", {
            "draft": "Ayunika Bright Serum sudah halal dan dijamin bikin glowing dalam 3 hari.",
            "sku": "AY-SR-101",
            "platform": "tiktok",
        })
        isi = _isi(hasil)
        cek("verdict TOLAK", isi.get("verdict") == "TOLAK", isi.get("verdict"))
        aturan = {t["rule_id"] for t in isi.get("temuan", [])}
        cek("R-03 tertangkap", "R-03" in aturan, sorted(aturan))
        cek("R-07 tertangkap", "R-07" in aturan, sorted(aturan))

        print("\n4. run_cycle berhenti sebelum terbit")
        hasil = await client.call_tool("run_cycle", {"sku": "AY-SR-101", "platform": "tiktok"})
        isi = _isi(hasil)
        cek("status bukan TERBIT", isi.get("status") != "TERBIT", isi.get("status"))
        cek("status diizinkan",
            isi.get("status") in ("LOLOS", "PERLU_DATA", "ESKALASI"), isi.get("status"))

        print("\n5. approval: usul lalu setujui")
        usul = _isi(await client.call_tool("request_approval", {
            "sku": "AY-SR-101", "platform": "tiktok", "content": "konten uji",
        }))
        cek("status PROPOSED", usul.get("status") == "PROPOSED", usul)

        salah = _isi(await client.call_tool("approve_publication", {
            "plan_id": usul.get("plan_id", ""), "approval_key": KUNCI_ASING,
        }))
        cek("kunci yang tidak cocok ditolak lewat protokol",
            salah.get("error") == "approval_key_salah", salah)

        sah = _isi(await client.call_tool("approve_publication", {
            "plan_id": usul.get("plan_id", ""), "approval_key": KUNCI,
        }))
        cek("persetujuan manusia diterima", sah.get("status") == "APPROVED", sah)
        cek("approver diturunkan dari kunci", sah.get("approver") == "Agung",
            sah.get("approver"))

        print("\n6. audit")
        verifikasi = _isi(await client.call_tool("audit_verify", {}))
        cek("rantai utuh", verifikasi.get("utuh") is True, verifikasi)

    print("\n" + "-" * 62)
    if GAGAL:
        print(f"GAGAL {len(GAGAL)} pemeriksaan: {GAGAL}")
        return 1
    print("LULUS semua pemeriksaan protokol stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(anyio.run(main))
