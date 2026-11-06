// index.js — BFF situs publik Lolos. Tanpa dependensi (Node >= 20).
//
// Tiga aturan yang dipegang berkas ini:
//
//  1. MCP_TOKEN hanya hidup di sini. Browser tidak pernah melihatnya.
//  2. Hanya EMPAT tool yang boleh dijangkau pengunjung: list_products,
//     run_cycle, request_approval, audit_tail. `approve_publication` sengaja
//     TIDAK ada di berkas ini — persetujuan hanya dari sesi WorkBuddy pemilik,
//     dengan kunci approver yang tidak pernah menyentuh server ini.
//  3. Batas per IP di memori. Cukup untuk satu proses demo; hilang saat restart.
import http from "node:http";
import { readFile } from "node:fs/promises";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { buatKlien } from "./mcp.js";

const PORT = Number(process.env.PORT || 8080);
const MCP_URL = (process.env.MCP_URL || "").trim();
const MCP_TOKEN = (process.env.MCP_TOKEN || "").trim();

// Penjelas (opsi C). Kosong = fitur chat disembunyikan, bukan error.
const LLM_BASE_URL = (process.env.LLM_BASE_URL || "").trim().replace(/\/+$/, "");
const LLM_API_KEY = (process.env.LLM_API_KEY || "").trim();
const LLM_MODEL = (process.env.LLM_MODEL || "").trim();
const PENJELAS_SIAP = Boolean(LLM_BASE_URL && LLM_API_KEY && LLM_MODEL);

if (!MCP_URL || !MCP_TOKEN) {
  console.error("MCP_URL dan MCP_TOKEN wajib diisi. Lihat web/.env.example.");
  process.exit(2);
}

const PUBLIK = resolve(dirname(fileURLToPath(import.meta.url)), "..", "public");
const klien = buatKlien({ url: MCP_URL, token: MCP_TOKEN });

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

const BATAS = {
  run: { maks: 5, jendela: 60 * 60 * 1000 },
  propose: { maks: 10, jendela: 60 * 60 * 1000 },
  explain: { maks: 20, jendela: 60 * 60 * 1000 },
};
const jejak = new Map();

function ipDari(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd) return fwd.split(",")[0].trim();
  return req.socket.remoteAddress || "?";
}

function boleh(ip, jenis) {
  const b = BATAS[jenis];
  const sekarang = Date.now();
  const kunci = `${jenis}:${ip}`;
  const catat = jejak.get(kunci);
  if (!catat || sekarang > catat.reset) {
    jejak.set(kunci, { sisa: b.maks - 1, reset: sekarang + b.jendela });
    return { ok: true, sisa: b.maks - 1 };
  }
  if (catat.sisa <= 0) {
    return { ok: false, detik: Math.ceil((catat.reset - sekarang) / 1000) };
  }
  catat.sisa -= 1;
  return { ok: true, sisa: catat.sisa };
}

function kirim(res, status, data) {
  const badan = JSON.stringify(data);
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  res.end(badan);
}

async function bacaJson(req) {
  let ukuran = 0;
  const potong = [];
  for await (const bagian of req) {
    ukuran += bagian.length;
    if (ukuran > 64 * 1024) throw new Error("body terlalu besar");
    potong.push(bagian);
  }
  if (!potong.length) return {};
  try {
    return JSON.parse(Buffer.concat(potong).toString("utf8"));
  } catch {
    throw new Error("body bukan JSON");
  }
}

const PLATFORM = new Set(["tiktok", "instagram", "marketplace"]);
const SKU_RE = /^AY-[A-Z]{2}-\d{3}$/;
const PLAN_RE = /^PLAN-[0-9A-F]{8}$/;

const cekSku = (v) => typeof v === "string" && SKU_RE.test(v);
const cekPlatform = (v) => typeof v === "string" && PLATFORM.has(v);

// --------------------------------------------------------------------------- penjelas (opsi C)
// Model di sini HANYA menjelaskan keputusan mesin aturan. Ia tidak menulis
// konten, tidak punya tool, dan tidak pernah melihat kunci approval. Kalau ia
// mengarang fakta, verdict tidak berubah — verdict milik kode, bukan model.
const SISTEM_PENJELAS = `Kamu menjelaskan keputusan mesin aturan klaim kosmetik kepada pengunjung situs.

Aturan yang mengikat:
- Kamu BUKAN penulis konten. Jangan menulis caption, naskah, atau kalimat marketing.
- Jangan mengarang fakta: harga, nomor BPOM, kadar bahan, status halal, sertifikat.
- Jawab HANYA dari data temuan yang diberikan. Bila tidak ada di sana, katakan tidak tersedia.
- Bahasa Indonesia, maksimal 120 kata, tanpa emoji, tanpa menyebut dirimu sebagai AI.

Tugasmu: menjelaskan mengapa verdict itu keluar dan apa yang harus diperbaiki.`;

function rapikanTemuan(daftar) {
  return (Array.isArray(daftar) ? daftar : []).slice(0, 20).map((t) => ({
    rule_id: String(t.rule_id ?? "").slice(0, 12),
    span: String(t.span ?? "").slice(0, 300),
    reason: String(t.reason ?? "").slice(0, 300),
    fix: String(t.fix ?? "").slice(0, 300),
  }));
}

async function tanyaPenjelas({ pertanyaan, verdict, sku, temuan }) {
  const kendali = new AbortController();
  const jam = setTimeout(() => kendali.abort(), 25_000);
  try {
    const res = await fetch(`${LLM_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${LLM_API_KEY}`,
      },
      body: JSON.stringify({
        model: LLM_MODEL,
        temperature: 0.2,
        max_tokens: 400,
        messages: [
          { role: "system", content: SISTEM_PENJELAS },
          {
            role: "user",
            content: JSON.stringify({ pertanyaan, sku, verdict, temuan }),
          },
        ],
      }),
      signal: kendali.signal,
    });
    const teks = await res.text();
    if (!res.ok) throw new Error(`LLM ${res.status}: ${teks.slice(0, 160)}`);
    const data = JSON.parse(teks);
    const jawab = data?.choices?.[0]?.message?.content;
    if (!jawab) throw new Error("balasan model kosong");
    return String(jawab).trim();
  } finally {
    clearTimeout(jam);
  }
}

async function tanganiApi(req, res, url) {
  const ip = ipDari(req);

  if (req.method === "GET" && url.pathname === "/api/products") {
    return kirim(res, 200, await klien.panggilTool("list_products", {}));
  }

  if (req.method === "POST" && url.pathname === "/api/run") {
    const jatah = boleh(ip, "run");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas review tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    const body = await bacaJson(req);
    if (!cekSku(body.sku) || !cekPlatform(body.platform)) {
      return kirim(res, 400, { error: "sku atau platform tidak sah" });
    }
    const angle = typeof body.angle === "string" ? body.angle.trim().slice(0, 120) : "";
    const data = await klien.panggilTool("run_cycle", {
      sku: body.sku,
      platform: body.platform,
      ...(angle ? { angle } : {}),
    });
    return kirim(res, 200, { ...data, sisa_jatah: jatah.sisa });
  }

  if (req.method === "POST" && url.pathname === "/api/propose") {
    const jatah = boleh(ip, "propose");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas pengajuan tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    const body = await bacaJson(req);
    if (!cekSku(body.sku) || !cekPlatform(body.platform)) {
      return kirim(res, 400, { error: "sku atau platform tidak sah" });
    }
    if (typeof body.content !== "string" || !body.content.trim()) {
      return kirim(res, 400, { error: "konten kosong" });
    }
    if (body.content.length > 5000) {
      return kirim(res, 400, { error: "konten melebihi 5000 karakter" });
    }
    const data = await klien.panggilTool("request_approval", {
      sku: body.sku,
      platform: body.platform,
      content: body.content,
    });
    return kirim(res, 200, { ...data, sisa_jatah: jatah.sisa });
  }

  if (req.method === "GET" && url.pathname === "/api/status") {
    const plan = url.searchParams.get("plan_id") || "";
    if (!PLAN_RE.test(plan)) {
      return kirim(res, 400, { error: "plan_id tidak sah" });
    }
    const tail = await klien.panggilTool("audit_tail", { n: 100 });
    const entri = tail.entri || [];
    const setuju = entri.find((e) => e.action === "plan_approve" && e.target === plan);
    const tolak = entri.find((e) => e.action === "plan_reject" && e.target === plan);
    return kirim(res, 200, {
      plan_id: plan,
      status: setuju ? "APPROVED" : tolak ? "REJECTED" : "PROPOSED",
      approver: setuju?.actor ?? null,
      waktu: setuju?.ts ?? null,
      jumlah_entri: entri.length,
    });
  }

  if (req.method === "GET" && url.pathname === "/api/config") {
    return kirim(res, 200, { penjelas: PENJELAS_SIAP });
  }

  if (req.method === "POST" && url.pathname === "/api/explain") {
    if (!PENJELAS_SIAP) {
      return kirim(res, 501, {
        error: "penjelas belum dikonfigurasi: isi LLM_BASE_URL, LLM_API_KEY, LLM_MODEL",
      });
    }
    const jatah = boleh(ip, "explain");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas tanya tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    const body = await bacaJson(req);
    const pertanyaan = typeof body.question === "string" ? body.question.trim() : "";
    if (!pertanyaan) return kirim(res, 400, { error: "pertanyaan kosong" });
    if (pertanyaan.length > 500) {
      return kirim(res, 400, { error: "pertanyaan melebihi 500 karakter" });
    }
    const jawaban = await tanyaPenjelas({
      pertanyaan,
      verdict: String(body.verdict ?? "").slice(0, 20),
      sku: cekSku(body.sku) ? body.sku : "",
      temuan: body.temuan,
    });
    return kirim(res, 200, { jawaban, sisa_jatah: jatah.sisa });
  }

  return kirim(res, 404, { error: "tidak ada" });
}

async function layaniStatis(res, pathname) {
  const rel = pathname === "/" ? "index.html" : pathname;
  const penuh = resolve(PUBLIK, rel.startsWith("/") ? "." + rel : rel);
  if (penuh !== PUBLIK && !penuh.startsWith(PUBLIK + sep)) {
    res.writeHead(403, { "content-type": "text/plain; charset=utf-8" });
    return res.end("terlarang");
  }
  try {
    const isi = await readFile(penuh);
    res.writeHead(200, {
      "content-type": MIME[extname(penuh)] || "application/octet-stream",
      "cache-control": "no-cache",
    });
    res.end(isi);
  } catch {
    res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    res.end("tidak ditemukan");
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  try {
    if (url.pathname.startsWith("/api/")) {
      return await tanganiApi(req, res, url);
    }
    if (req.method !== "GET" && req.method !== "HEAD") {
      res.writeHead(405, { allow: "GET, HEAD" });
      return res.end();
    }
    return await layaniStatis(res, url.pathname);
  } catch (e) {
    console.error("[bff]", e.message);
    if (!res.headersSent) {
      return kirim(res, 502, {
        error: "gagal menghubungi MCP",
        detail: String(e.message).slice(0, 200),
      });
    }
    res.end();
  }
});

server.listen(PORT, () => {
  console.log(`lolos-web di http://localhost:${PORT}`);
  console.log(`MCP: ${MCP_URL}`);
});
