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

# MCP_URL TIDAK di-hardcode di sini. Domain layanan bisa berubah (dan pernah
# berubah), dan nilai yang tertanam di image akan menunjuk host mati tanpa
# ketahuan. Set sebagai Variable di platform, idealnya dengan referensi:
#   MCP_URL=https://${{lolos-mcp.RAILWAY_PUBLIC_DOMAIN}}/mcp
# Tanpa MCP_URL, container menolak start — gagal keras, bukan gagal diam-diam.
EXPOSE 8080

# PORT disuntik platform (Railway); BFF membaca process.env.PORT.
# /health tersedia untuk healthcheck.
CMD ["node", "server/index.js"]
