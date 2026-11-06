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
EXPOSE 8080

# PORT disuntik platform (Railway); BFF membaca process.env.PORT.
# /health tersedia untuk healthcheck.
CMD ["node", "server/index.js"]
