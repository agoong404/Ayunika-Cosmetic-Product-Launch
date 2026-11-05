# Untuk host berbasis kontainer (Cloud Run, Fly.io, VPS dengan Docker).
# Build dari root repo:
#   docker build -f deploy/Dockerfile -t lolos-mcp .
#
# engine/.audit/ TIDAK ikut ke image (gitignored). Pasang volume di
# /app/engine/.audit kalau rantai audit harus bertahan melewati restart.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

WORKDIR /app

COPY requirements-mcp.txt ./
RUN pip install --no-cache-dir -r requirements-mcp.txt

COPY engine/ ./engine/
COPY agents/ ./agents/
COPY dataset_c/ ./dataset_c/
COPY mcp_server/ ./mcp_server/
COPY deploy/entrypoint.sh /app/entrypoint.sh

RUN mkdir -p /app/engine/.audit \
    && chmod +x /app/entrypoint.sh \
    && useradd --create-home --shell /usr/sbin/nologin lolos \
    && chown -R lolos:lolos /app

# Sengaja TANPA `USER lolos`: entrypoint harus mulai sebagai root untuk
# menyesuaikan pemilik folder audit milik volume, lalu turun sendiri ke `lolos`
# lewat setpriv/su. Menaruh `USER lolos` di sini membuat chown itu mustahil.
EXPOSE 8000

# Satu worker. ApprovalGate hidup di memori dan AuditLog mengasumsikan satu penulis.
ENTRYPOINT ["/app/entrypoint.sh"]
