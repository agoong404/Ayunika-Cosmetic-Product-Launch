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
    const data = await klien.panggilTool("run_cycle", {
      sku: body.sku,
      platform: body.platform,
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
