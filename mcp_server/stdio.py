"""
stdio.py — titik masuk transport stdio.

WorkBuddy menjalankan berkas ini sebagai proses anak dan berbicara lewat
stdin/stdout. Karena itu stdout adalah kabel protokol: tidak boleh ada satu
`print()` pun di jalur ini. Diagnosis, bila perlu, lewat `logging` ke stderr.

Pemakaian:
    .venv\\Scripts\\python.exe -m mcp_server.stdio
"""
from __future__ import annotations

import logging
import sys

from .server import mcp


def main() -> None:
    # stderr, bukan stdout. Baris ini membantu saat WorkBuddy gagal menyambung.
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
