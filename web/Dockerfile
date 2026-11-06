# Dockerfile untuk layanan web (BFF + frontend). Konteks build = folder web/.
#
# Sengaja tanpa `npm install`: package.json tidak punya dependensi. Kalau nanti
# ditambah, buka dua baris di bawah.
FROM node:22-alpine

WORKDIR /app

COPY package.json ./
# COPY package-lock.json ./
# RUN npm install --omit=dev

COPY server/ ./server/
COPY public/ ./public/

ENV NODE_ENV=production
# Default non-rahasia. Bisa ditimpa lewat Variables platform kapan saja.
# Hanya MCP_TOKEN yang wajib diisi manual — itu rahasia, tidak boleh di image.
ENV MCP_URL=https://ayunika-cosmetic-product-launch-production.up.railway.app/mcp
EXPOSE 8080

# PORT disuntik platform (Railway); BFF membaca process.env.PORT.
# /health tersedia untuk healthcheck.
CMD ["node", "server/index.js"]
