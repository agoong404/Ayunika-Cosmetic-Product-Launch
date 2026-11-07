// index.js — BFF situs publik Ayunika Care. Tanpa dependensi (Node >= 20).
//
// Tiga aturan yang dipegang berkas ini:
//
//  1. MCP_TOKEN hanya hidup di sini. Browser tidak pernah melihatnya.
//  2. Tool yang boleh dijangkau pengunjung: list_products, get_rulebook,
//     run_cycle, review_draft, request_approval, audit_tail. `approve_publication`
//     sengaja TIDAK ada di berkas ini — persetujuan hanya dari sesi WorkBuddy
//     pemilik, dengan kunci approver yang tidak pernah menyentuh server ini.
//     `review_draft` read-only (lapis deterministik, tanpa LLM) jadi aman
//     diekspos: menunjukkan penolakan sebelum draf jadi kasus yang disetujui.
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
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

const BATAS = {
  run: { maks: 5, jendela: 60 * 60 * 1000 },
  review: { maks: 15, jendela: 60 * 60 * 1000 },
  propose: { maks: 10, jendela: 60 * 60 * 1000 },
  upload: { maks: 10, jendela: 60 * 60 * 1000 },
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

// --------------------------------------------------------------------------- pilihan sudut (tanpa LLM)
// Satu-satunya masukan yang sah. Pengunjung memilih dari daftar ini; teks bebas
// ditolak dengan pesan yang jelas, bukan ditebak-tebak. Daftar ini juga yang
// memvalidasi /api/run, jadi bukan hanya UI yang menahannya.
const SUDUT_PILIHAN = [
  { label: "bahan aktif", angle: "Jelaskan bahan aktif dan kadarnya" },
  { label: "tekstur ringan", angle: "Tekankan tekstur ringan dan cepat meresap" },
  { label: "kulit kusam", angle: "Ditujukan untuk kulit kusam" },
  { label: "promo peluncuran", angle: "Sebutkan promo peluncuran dan kuotanya" },
];

const PESAN_TOLAK =
  "Maaf, hanya empat pilihan itu yang bisa dipakai. " +
  "Silakan pilih salah satu tombol di atas.";

function pilihSudut(teks) {
  const t = String(teks || "").trim().toLowerCase();
  for (const s of SUDUT_PILIHAN) {
    if (t === s.angle.toLowerCase() || t === s.label.toLowerCase()) {
      return { cocok: true, angle: s.angle, pesan: "" };
    }
  }
  return { cocok: false, angle: "", pesan: PESAN_TOLAK };
}

const cekSku = (v) => typeof v === "string" && SKU_RE.test(v);
const cekPlatform = (v) => typeof v === "string" && PLATFORM.has(v);

async function tanganiApi(req, res, url) {
  const ip = ipDari(req);

  if (req.method === "GET" && url.pathname === "/api/products") {
    return kirim(res, 200, await klien.panggilTool("list_products", {}));
  }

  if (req.method === "GET" && url.pathname === "/api/sudut") {
    return kirim(res, 200, { pilihan: SUDUT_PILIHAN });
  }

  if (req.method === "POST" && url.pathname === "/api/pilih") {
    const body = await bacaJson(req);
    const pilihan = typeof body.pilihan === "string" ? body.pilihan.trim() : "";
    if (!pilihan) return kirim(res, 400, { error: "pilihan kosong" });
    if (pilihan.length > 200) {
      return kirim(res, 400, { error: "pilihan melebihi 200 karakter" });
    }
    return kirim(res, 200, { ...pilihSudut(pilihan), pilihan });
  }

  if (req.method === "POST" && url.pathname === "/api/rulebook") {
    const body = await bacaJson(req);
    const ids = Array.isArray(body.ids) ? body.ids : [];
    const bersih = ids
      .filter((v) => typeof v === "string" && /^R-\d{2}$/.test(v))
      .slice(0, 21);
    if (!bersih.length) return kirim(res, 400, { error: "ids kosong atau tidak sah" });
    return kirim(res, 200, await klien.panggilTool("get_rulebook", { rule_ids: bersih }));
  }

  if (req.method === "POST" && url.pathname === "/api/run") {
    // Validasi dulu, baru potong jatah: permintaan yang ditolak tidak boleh
    // menghabiskan kuota pengunjung.
    const body = await bacaJson(req);
    if (!cekSku(body.sku) || !cekPlatform(body.platform)) {
      return kirim(res, 400, { error: "sku atau platform tidak sah" });
    }
    const angle = typeof body.angle === "string" ? body.angle.trim() : "";
    if (angle && !SUDUT_PILIHAN.some((s) => s.angle === angle)) {
      return kirim(res, 400, { error: PESAN_TOLAK });
    }
    const jatah = boleh(ip, "run");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas review tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    const data = await klien.panggilTool("run_cycle", {
      sku: body.sku,
      platform: body.platform,
      ...(angle ? { angle } : {}),
    });
    return kirim(res, 200, { ...data, sisa_jatah: jatah.sisa });
  }

  if (req.method === "POST" && url.pathname === "/api/propose") {
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
    const jatah = boleh(ip, "propose");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas pengajuan tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    const data = await klien.panggilTool("request_approval", {
      sku: body.sku,
      platform: body.platform,
      content: body.content,
    });
    return kirim(res, 200, { ...data, sisa_jatah: jatah.sisa });
  }

  if (req.method === "POST" && url.pathname === "/api/run-relay") {
    // Rantai granular (plan_content -> write_draft + review_draft per iterasi)
    // supaya UI menampilkan draf tiap iterasi, bukan hanya verdict run_cycle.
    // Memanggil tool yang SAMA dengan run_cycle secara internal — tidak ada
    // perubahan di mcp_server/ atau engine/.
    const body = await bacaJson(req);
    if (!cekSku(body.sku) || !cekPlatform(body.platform)) {
      return kirim(res, 400, { error: "sku atau platform tidak sah" });
    }
    const angle = typeof body.angle === "string" ? body.angle.trim() : "";
    if (angle && !SUDUT_PILIHAN.some((s) => s.angle === angle)) {
      return kirim(res, 400, { error: PESAN_TOLAK });
    }
    const jatah = boleh(ip, "run");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas review tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    try {
      const rencana = await klien.panggilTool("plan_content", {
        sku: body.sku,
        platform: body.platform,
        ...(angle ? { angle } : {}),
      });
      if (!rencana.ok) {
        return kirim(res, 200, { ...rencana, sisa_jatah: jatah.sisa });
      }
      const plan = rencana.plan;
      const MAKS_ITERASI = 3;
      const riwayat = [];
      let draf = null;
      for (let it = 1; it <= MAKS_ITERASI; it++) {
        const tulis = await klien.panggilTool("write_draft", {
          plan,
          iteration: it,
          ...(it > 1 ? { feedback: riwayat[riwayat.length - 1].temuan } : {}),
        });
        if (!tulis.ok) {
          return kirim(res, 200, { ...tulis, plan, riwayat, sisa_jatah: jatah.sisa });
        }
        draf = tulis.draft;
        const nilai = await klien.panggilTool("review_draft", {
          draft: draf,
          sku: body.sku,
          platform: body.platform,
          iteration: it,
          write_audit: true,
        });
        if (!nilai.ok) {
          return kirim(res, 200, { ...nilai, plan, riwayat, sisa_jatah: jatah.sisa });
        }
        riwayat.push({
          iterasi: it,
          draf,
          verdict: nilai.verdict,
          jumlah_temuan: nilai.jumlah_temuan,
          temuan: nilai.temuan,
        });
        if (nilai.verdict === "LOLOS") {
          return kirim(res, 200, {
            ok: true, status: "LOLOS", iterasi: it,
            konten_final: draf, riwayat, plan,
            catatan: "Berhenti di LOLOS. Belum disetujui manusia.",
            sisa_jatah: jatah.sisa,
          });
        }
        if (nilai.verdict === "PERLU_DATA") {
          return kirim(res, 200, {
            ok: true, status: "PERLU_DATA", iterasi: it,
            konten_final: "", riwayat, plan,
            catatan: "PERLU_DATA bukan lulus: data produk tidak cukup untuk memverifikasi.",
            sisa_jatah: jatah.sisa,
          });
        }
      }
      return kirim(res, 200, {
        ok: true, status: "ESKALASI", iterasi: MAKS_ITERASI,
        konten_final: "", riwayat, plan,
        catatan: "Tiga iterasi tercapai. Eskalasi ke manusia dengan riwayat revisi.",
        sisa_jatah: jatah.sisa,
      });
    } catch (e) {
      return kirim(res, 502, {
        error: "gagal menghubungi MCP",
        detail: String(e.message).slice(0, 200),
      });
    }
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

  if (req.method === "POST" && url.pathname === "/api/upload-produk") {
    // Unggah Lembar Produk (PDF) -> ekstrak SKU -> validasi ke registri server.
    // Dokumen HANYA pengenal: isinya tidak pernah dianggap fakta (lihat NOTES.md).
    // pdf-parse diimpor DINAMIS agar BFF tetap boot walau dependensi belum
    // terpasang; kalau absen, rute mengembalikan 501 alih-alih menjebol server.
    const jatah = boleh(ip, "upload");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas unggah tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    let ukuran = 0;
    const potong = [];
    for await (const bagian of req) {
      ukuran += bagian.length;
      if (ukuran > 2 * 1024 * 1024) {
        return kirim(res, 413, { error: "file terlalu besar (maks 2MB)" });
      }
      potong.push(bagian);
    }
    if (!potong.length) return kirim(res, 400, { error: "berkas kosong" });
    const buffer = Buffer.concat(potong);

    let PDFParse;
    try {
      ({ PDFParse } = await import("pdf-parse"));
    } catch {
      return kirim(res, 501, { error: "fitur unggah belum tersedia di server ini." });
    }

    let teks = "";
    try {
      const parser = new PDFParse({ data: buffer });
      const hasil = await parser.getText();
      teks = hasil.text || "";
      await parser.destroy();
    } catch {
      return kirim(res, 400, {
        error: "Berkas tidak bisa dibaca sebagai PDF. Gunakan dropdown sebagai gantinya.",
      });
    }

    const cocokSku = teks.match(/SKU[\s\n]+(AY-[A-Z]{2}-\d{3})/);
    if (!cocokSku) {
      return kirim(res, 400, {
        error: "SKU tidak ditemukan di dokumen. Gunakan dropdown sebagai gantinya.",
      });
    }
    const sku = cocokSku[1];

    const produkData = await klien.panggilTool("list_products", {});
    const dikenal = (produkData.produk || []).some((p) => p.sku === sku);
    if (!dikenal) {
      return kirim(res, 400, {
        error: `SKU ${sku} tidak dikenali di registri. Gunakan dropdown sebagai gantinya.`,
      });
    }

    const cocokDoc = teks.match(/No\.\s*Dokumen[\s\n]+(PS-\d{3})/i);
    return kirim(res, 200, {
      ok: true,
      sku,
      doc_id: cocokDoc ? cocokDoc[1] : null,
      sisa_jatah: jatah.sisa,
      pesan: "Dokumen dikenali. Data produk akan ditarik dari server.",
    });
  }

  if (req.method === "POST" && url.pathname === "/api/review") {
    // Periksa draf bebas pengunjung terhadap aturan (lapis deterministik).
    // Read-only: tidak menulis rantai audit, tidak pernah menyetujui apa pun.
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
    const jatah = boleh(ip, "review");
    if (!jatah.ok) {
      return kirim(res, 429, {
        error: `Batas pemeriksaan tercapai. Coba lagi dalam ${jatah.detik} detik.`,
      });
    }
    const data = await klien.panggilTool("review_draft", {
      draft: body.content,
      sku: body.sku,
      platform: body.platform,
    });
    return kirim(res, 200, { ...data, status: data.verdict, sisa_jatah: jatah.sisa });
  }

  if (req.method === "GET" && url.pathname === "/api/audit") {
    // Tabel audit publik: panggil tool audit_tail (sudah termasuk 5 tool yang
    // diizinkan publik). Maks 100 entri.
    const n = Math.min(Number(url.searchParams.get("n")) || 20, 100);
    return kirim(res, 200, await klien.panggilTool("audit_tail", { n }));
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
    // Tanpa token, tanpa sentuh MCP: dipakai healthcheck Railway.
    if (url.pathname === "/health") {
      return kirim(res, 200, { status: "ok", service: "ayunika-care-web" });
    }
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
  console.log(`ayunika-care-web di http://localhost:${PORT}`);
  console.log(`MCP: ${MCP_URL}`);
});
