#!/bin/sh
# entrypoint.sh — siapkan folder audit milik volume, lalu turun ke user `lolos`.
#
# Kenapa ada: image ini berjalan sebagai `lolos` (non-root), sedangkan volume
# Railway/Docker ter-mount sebagai root:root. Tanpa chown di sini, setiap
# append ke rantai audit gagal (EACCES) dan semua tool yang menulis audit ikut
# error. Skrip ini selalu bisa jalan: kalau setpriv/su tidak ada, proses tetap
# dinaikkan sebagai root daripada container mati.
set -e

AUDIT_DIR="${HALAL_AUDIT_DIR:-/app/engine/.audit}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$AUDIT_DIR"
    chown -R lolos:lolos "$AUDIT_DIR" 2>/dev/null || true

    if command -v setpriv >/dev/null 2>&1; then
        exec setpriv --reuid=lolos --regid=lolos --init-groups python -m mcp_server
    elif command -v su >/dev/null 2>&1; then
        exec su lolos -s /bin/sh -c "python -m mcp_server"
    fi

    echo "PERINGATAN: setpriv/su tidak tersedia; berjalan sebagai root." >&2
fi

exec python -m mcp_server
