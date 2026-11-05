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

RUN mkdir -p /app/engine/.audit \
    && useradd --create-home --shell /usr/sbin/nologin lolos \
    && chown -R lolos:lolos /app
USER lolos

EXPOSE 8000

# Satu worker. ApprovalGate hidup di memori dan AuditLog mengasumsikan satu penulis.
CMD ["python", "-m", "mcp_server"]
