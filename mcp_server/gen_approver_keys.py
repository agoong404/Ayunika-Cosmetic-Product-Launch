"""
gen_approver_keys.py — buat kunci per manusia + JSON untuk MCP_APPROVER_KEYS.

Pemakaian:
    .venv\\Scripts\\python.exe -m mcp_server.gen_approver_keys Nama1 [Nama2 ...]

Aturannya sederhana dan tidak boleh dilanggar:

  - Kunci asli dicetak SEKALI di sini dan diserahkan ke manusianya. Server tidak
    pernah menyimpannya.
  - Yang masuk konfigurasi server (env MCP_APPROVER_KEYS atau berkas
    .approver_keys di root repo) hanya SHA-256 hex kuncinya. Server kompromi
    tidak membocorkan satu kunci pun yang bisa dipakai.
  - Satu kunci = satu manusia. Jangan bagikan satu kunci ke dua orang; dengan
    kunci per approver, atribusi di rantai audit hanya bermakna bila kunci
    benar-benar milik satu orang.

Rotate = jalankan lagi untuk nama yang sama, ganti nilai hash di konfigurasi.
Perhatikan: server restart akibat ganti konfigurasi mengosongkan gerbang
plan di memori — plan PROPOSED yang belum disetujui hilang.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sys


def main(argv: list[str]) -> int:
    nama_list = [a.strip() for a in argv if a.strip()]
    if not nama_list:
        print("pakai: python -m mcp_server.gen_approver_keys Nama1 [Nama2 ...]",
              file=sys.stderr)
        print("contoh: python -m mcp_server.gen_approver_keys Agung Budi",
              file=sys.stderr)
        return 2

    if len(set(nama_list)) != len(nama_list):
        print("nama approver tidak boleh kembar", file=sys.stderr)
        return 2

    print("Kunci asli — serahkan ke manusianya, jangan disimpan di server:\n")
    registri: dict[str, str] = {}
    for nama in nama_list:
        kunci = secrets.token_hex(32)
        registri[nama] = hashlib.sha256(kunci.encode("utf-8")).hexdigest()
        print(f"  {nama}")
        print(f"    kunci  : {kunci}")
        print(f"    sha256 : {registri[nama]}\n")

    print("Masukkan ke env MCP_APPROVER_KEYS (atau berkas .approver_keys):\n")
    print(json.dumps(registri, ensure_ascii=False))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
