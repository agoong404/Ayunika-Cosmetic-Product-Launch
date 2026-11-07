// preview-server.js — pratinjau lokal TANPA MCP. Menyajikan public/ dan
// memalsukan /api/* dengan data contoh. Bukan untuk deploy (lihat NOTES.md §9).
//
// /api/upload-produk TIDAK dipalsukan — memakai pdf-parse sungguhan (API v2, class-based)
// persis seperti backend-patch/upload-produk.route.js, supaya pengujian unggah dokumen
// di pratinjau ini benar-benar representatif, bukan sekadar echo nama file.
import http from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { PDFParse } from "pdf-parse";

const DIR = fileURLToPath(new URL("./public", import.meta.url));
const PORT = Number(process.env.PORT) || 8099;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
};

const PRODUK = [
  { sku: "AY-SR-101", nama: "Ayunika Bright Serum" },
  { sku: "AY-BL-102", nama: "Ayunika Glow Body Lotion" },
  { sku: "AY-FW-103", nama: "Ayunika Gentle Cleanser" },
  { sku: "AY-SC-104", nama: "Ayunika Coffee Scrub" },
];

// Disalin PERSIS dari web/server/index.js (SUDUT_PILIHAN) di repo utama — jangan diubah
// tanpa menyamakan juga di sana. Mismatch label/angle antara mock ini dan backend
// sungguhan akan membuat /api/run-relay menolak permintaan (PESAN_TOLAK).
const SUDUT = [
  { label: "bahan aktif", angle: "Jelaskan bahan aktif dan kadarnya" },
  { label: "tekstur ringan", angle: "Tekankan tekstur ringan dan cepat meresap" },
  { label: "kulit kusam", angle: "Ditujukan untuk kulit kusam" },
  { label: "promo peluncuran", angle: "Sebutkan promo peluncuran dan kuotanya" },
];

function kirimJson(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(body);
}

async function baca(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString("utf-8") || "{}";
  try { return JSON.parse(raw); } catch { return {}; }
}

const PLAN_STORE = new Map();

async function tanganiApi(req, res, url) {
  if (req.method === "GET" && url.pathname === "/api/products") {
    return kirimJson(res, 200, { produk: PRODUK });
  }
  if (req.method === "GET" && url.pathname === "/api/sudut") {
    return kirimJson(res, 200, { pilihan: SUDUT });
  }
  if (req.method === "POST" && url.pathname === "/api/upload-produk") {
    let ukuran = 0;
    const potong = [];
    for await (const bagian of req) {
      ukuran += bagian.length;
      if (ukuran > 2 * 1024 * 1024) {
        return kirimJson(res, 413, { ok: false, error: "file terlalu besar (maks 2MB)" });
      }
      potong.push(bagian);
    }
    if (!potong.length) return kirimJson(res, 400, { ok: false, error: "berkas kosong" });
    const buffer = Buffer.concat(potong);

    let teks = "";
    try {
      const parser = new PDFParse({ data: buffer });
      const hasil = await parser.getText();
      teks = hasil.text || "";
      await parser.destroy();
    } catch {
      return kirimJson(res, 400, {
        ok: false,
        error: "Berkas tidak bisa dibaca sebagai PDF. Gunakan dropdown sebagai gantinya.",
      });
    }

    const cocokSku = teks.match(/SKU[\s\n]+(AY-[A-Z]{2}-\d{3})/);
    if (!cocokSku) {
      return kirimJson(res, 400, {
        ok: false,
        error: "SKU tidak ditemukan di dokumen. Gunakan dropdown sebagai gantinya.",
      });
    }
    const sku = cocokSku[1];
    const dikenal = PRODUK.some((p) => p.sku === sku);
    if (!dikenal) {
      return kirimJson(res, 400, {
        ok: false,
        error: `SKU ${sku} tidak dikenali di registri. Gunakan dropdown sebagai gantinya.`,
      });
    }
    const cocokDoc = teks.match(/No\.\s*Dokumen[\s\n]+(PS-\d{3})/i);
    return kirimJson(res, 200, {
      ok: true,
      sku,
      doc_id: cocokDoc ? cocokDoc[1] : null,
      sisa_jatah: 9,
      pesan: "Dokumen dikenali. Data produk akan ditarik dari server.",
    });
  }
  if (req.method === "POST" && (url.pathname === "/api/run-relay" || url.pathname === "/api/run")) {
    const body = await baca(req);
    const sku = body.sku || PRODUK[0].sku;
    const platform = body.platform || "tiktok";
    const produk = PRODUK.find((p) => p.sku === sku);
    if (sku === "AY-ZZ-999" || !produk) {
      return kirimJson(res, 200, {
        status: "PERLU_DATA",
        catatan: "SKU tidak ada di registri — harga, BPOM, halal, dan izin tidak dapat diverifikasi.",
        riwayat: [],
        sisa_jatah: 4,
      });
    }
    return kirimJson(res, 200, {
      status: "LOLOS",
      iterasi: 1,
      plan: {
        angle: body.angle || "manfaat",
        struktur: ["hook", "manfaat", "CTA"],
        fakta_boleh: ["niacinamide 5%", "tekstur ringan, cepat meresap"],
        fakta_dilarang: ["menyembuhkan jerawat", "hasil instan"],
      },
      riwayat: [
        {
          iterasi: 1,
          verdict: "LOLOS",
          draf: `Serum dengan niacinamide 5% untuk kulit kusam. Membantu mencerahkan tampilan kulit — cocok untuk ${platform}.`,
          temuan: [],
        },
      ],
      konten_final: `Serum dengan niacinamide 5% untuk kulit kusam. Membantu mencerahkan tampilan kulit — cocok untuk ${platform}.`,
      sisa_jatah: 4,
      catatan: `Pratinjau lokal (mock) untuk ${produk.nama}. Endpoint /api/run-relay sungguhan akan menampilkan draf per iterasi dari write_draft/review_draft live.`,
    });
  }
  if (req.method === "POST" && url.pathname === "/api/propose") {
    const body = await baca(req);
    const planId = `plan-${Date.now()}`;
    PLAN_STORE.set(planId, { status: "PROPOSED", createdAt: Date.now(), sku: body.sku });
    return kirimJson(res, 200, { plan_id: planId, kedaluwarsa_menit: 30 });
  }
  if (req.method === "GET" && url.pathname === "/api/status") {
    const planId = url.searchParams.get("plan_id");
    const plan = PLAN_STORE.get(planId);
    if (!plan) return kirimJson(res, 404, { error: "plan tidak ditemukan" });
    const umurDetik = (Date.now() - plan.createdAt) / 1000;
    if (umurDetik > 8 && plan.status === "PROPOSED") plan.status = "APPROVED";
    return kirimJson(res, 200, {
      status: plan.status,
      approver: plan.status === "APPROVED" ? "EMP-PREVIEW (mock)" : undefined,
      waktu: new Date().toISOString(),
      jumlah_entri: 3,
    });
  }
  if (req.method === "GET" && url.pathname === "/api/audit") {
    const n = Math.min(Number(url.searchParams.get("n")) || 20, 100);
    const entri = Array.from({ length: Math.min(n, 6) }, (_, i) => ({
      seq: i + 1,
      ts: new Date(Date.now() - (6 - i) * 60000).toISOString(),
      actor: ["rani", "bima", "citra", "dimas", "rani", "human"][i] || "sys",
      action: ["plan", "write", "review", "plan_propose", "plan_approve"][i] || "execute",
      target: "AY-SR-101",
      result: i === 2 ? "LOLOS" : "ok",
    }));
    return kirimJson(res, 200, { entri });
  }
  if (req.method === "POST" && url.pathname === "/api/rulebook") {
    return kirimJson(res, 200, { aturan: [] });
  }
  return kirimJson(res, 404, { error: "mock: rute tidak dikenal" });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (url.pathname.startsWith("/api/")) {
    try {
      return await tanganiApi(req, res, url);
    } catch (e) {
      return kirimJson(res, 500, { error: e.message });
    }
  }

  let filePath = join(DIR, url.pathname === "/" ? "index.html" : url.pathname);
  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(DIR, "index.html");
  }
  const ext = extname(filePath);
  res.writeHead(200, { "content-type": MIME[ext] || "application/octet-stream" });
  createReadStream(filePath).pipe(res);
});

server.listen(PORT, () => {
  console.log(`Preview (mock, tanpa MCP) jalan di http://localhost:${PORT}`);
});
