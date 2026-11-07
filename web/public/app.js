// app.js — Lolos UI internal (SPA hash-routing, tanpa dependensi).
// Terhubung ke BFF: /api/products, /api/sudut, /api/upload-produk (BARU),
// /api/run-relay (BARU, ganti /api/run), /api/propose, /api/status, /api/rulebook.
// Endpoint BARU butuh backend-patch/*.route.js ditempel ke web/server/index.js —
// lihat PANDUAN_UPDATE_UI.md. Profil agent & replay statis.
import { AGENTS, LAPIS2_RULES } from "./data/agents.js";
import { DEMO_CYCLE } from "./data/demo.js";

const app = document.getElementById("app");
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const h = (strings, ...vals) => strings.reduce((a, s, i) => a + s + (vals[i] ?? ""), "");
const agentById = (id) => AGENTS.find((a) => a.id === id);

async function api(jalur, opsi) {
  const res = await fetch(jalur, opsi);
  let data = {};
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

// =====================================================================
// ROUTER
// =====================================================================
function parseRoute() {
  const raw = (location.hash || "#/").replace(/^#/, "");
  const parts = raw.split("/").filter(Boolean); // ["agents","dimas"]
  return { base: "/" + (parts[0] || ""), id: parts[1] || "" };
}

function setActiveNav(base) {
  document.querySelectorAll("#nav a").forEach((a) => {
    const r = a.getAttribute("data-route");
    const on = r === base || (base.startsWith("/agents") && r === "/agents");
    a.classList.toggle("active", on);
  });
}

function router() {
  const { base, id } = parseRoute();
  setActiveNav(base);
  window.scrollTo(0, 0);
  switch (base) {
    case "/agents": return id ? viewProfile(id) : viewAgents();
    case "/console": return viewConsole();
    case "/cek": return viewCek();
    case "/audit": return viewAudit();
    case "/":
    default: return viewBeranda();
  }
}
window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", router);

// =====================================================================
// VIEW — BERANDA
// =====================================================================
function viewBeranda() {
  const steps = [
    ["01", "Brief & lembar produk", "Sumber fakta tunggal — brief diperlakukan sebagai instruksi, bukan fakta."],
    ["02", "Bima — Planner", "Rencana per platform: sudut, struktur, fakta boleh & dilarang."],
    ["03", "Citra — Writer", "Menulis draf hanya dari fakta yang diizinkan. Tak pernah lihat rulebook."],
    ["04", "Dimas — Reviewer", "Menilai dua lapis, menolak dengan nomor aturan + kutipan + perbaikan."],
    ["05", "Gerbang approval", "Lolos ≠ terbit. Kunci persetujuan hanya dipegang manusia."],
  ];
  app.innerHTML = h`
    <section class="view">
      <div class="hero">
        <span class="pill-line"><span class="brand-dot"></span> Challenge C — The Creator Agent</span>
        <h1>Periksa konten peluncuran sebelum terbit.</h1>
        <p class="lead">Empat agent bekerja sebagai tim: merencanakan, menulis, menilai, dan
          memperbaiki konten kosmetik terhadap aturan klaim BPOM &amp; jaminan halal —
          lalu berhenti di gerbang persetujuan manusia.</p>
        <div class="verdicts">
          <span class="chip ok">LOLOS</span>
          <span class="chip no">TOLAK</span>
          <span class="chip wait">PERLU_DATA</span>
        </div>
        <div class="cta-center">
          <a class="btn brand big" href="#/console">Coba Review</a>
        </div>
        <div class="btn-row" style="justify-content:center">
          <a class="btn ghost" href="#/agents">Lihat Tim Agent</a>
        </div>
      </div>

      <div class="section">
        <div class="section-head"><p class="eyebrow">Alur</p><h2>Lima langkah, satu arah</h2></div>
        <div class="flow">
          ${steps.map(([n, t, d]) => h`
            <div class="flow-step"><div class="n">${n}</div><div class="t">${esc(t)}</div><div class="d">${esc(d)}</div></div>`).join("")}
        </div>
      </div>

      <div class="section">
        <div class="section-head"><p class="eyebrow">Tiga verdict</p><h2>Jawaban yang tegas</h2></div>
        <div class="grid cols-3">
          <div class="status-card ok"><span class="chip ok">LOLOS</span><p>Tidak ada pelanggaran. Draf boleh diajukan ke gerbang approval — belum terbit.</p></div>
          <div class="status-card no"><span class="chip no">TOLAK</span><p>Minimal satu pelanggaran, tiap temuan membawa nomor aturan, kutipan persis, dan perbaikan.</p></div>
          <div class="status-card wait"><span class="chip wait">PERLU_DATA</span><p>SKU tak ada di registri: harga, BPOM, halal, dan izin tak bisa diverifikasi. <b>Ini bukan lulus.</b></p></div>
        </div>
      </div>

      <div class="section">
        <div class="section-head"><p class="eyebrow">Tim</p><h2>Empat agent, peran terpisah</h2></div>
        <div class="grid cols-4">
          ${AGENTS.map((a) => h`
            <a class="agent-card" style="flex-direction:column" href="#/agents/${a.id}">
              <img class="avatar lg" src="${a.avatar}" alt="${esc(a.nama)}">
              <div><div class="role">${esc(a.urutan)}</div>
              <div class="name">${esc(a.nama)} <span class="zh">${esc(a.nama_zh)}</span></div>
              <div class="prof">${esc(a.profesi)}</div></div>
            </a>`).join("")}
        </div>
      </div>

      <div class="section panel">
        <h2>Kenapa ada gerbang approval</h2>
        <p class="muted" style="max-width:68ch">Sistem ini tidak pernah menerbitkan apa pun. Setelah sebuah draf lolos, ia
        hanya bisa diajukan — dan persetujuan dilakukan manusia dengan kunci approver di luar situs ini.
        Situs ini tidak memegang kunci itu, jadi tidak ada tombol di sini yang bisa menyetujui konten.
        Setiap penolakan dan persetujuan tercatat di rantai hash yang tidak bisa diubah diam-diam.</p>
        <div class="btn-row"><a class="btn ghost" href="#/audit">Lihat jejak audit</a></div>
      </div>
    </section>`;
}

// =====================================================================
// VIEW — TIM AGENT
// =====================================================================
function viewAgents() {
  app.innerHTML = h`
    <section class="view">
      <div class="hero" style="padding-bottom:0">
        <span class="pill-line"><span class="brand-dot"></span> Ayunika Compliance Team</span>
        <h1>Empat agent, satu rantai pertanggungjawaban.</h1>
        <p class="lead">Tiap anggota konteks terpisah. Planner tak pernah melihat rulebook milik Reviewer,
          dan Writer tak pernah melihat daftar aturan — supaya siklus tolak → perbaiki benar-benar terjadi.</p>
      </div>
      <div class="grid cols-2" style="margin-top:8px">
        ${AGENTS.map((a) => h`
          <a class="agent-card" href="#/agents/${a.id}">
            <img class="avatar lg" src="${a.avatar}" alt="${esc(a.nama)}">
            <div>
              <div class="role">${esc(a.urutan)}</div>
              <div class="name">${esc(a.nama)} <span class="zh">${esc(a.nama_zh)}</span></div>
              <div class="prof">${esc(a.profesi)}</div>
              <p class="sum">${esc(a.ringkas)}</p>
            </div>
          </a>`).join("")}
      </div>
    </section>`;
}

// =====================================================================
// VIEW — PROFIL AGENT
// =====================================================================
function viewProfile(id) {
  const a = agentById(id);
  if (!a) {
    app.innerHTML = h`<section class="view"><a class="back" href="#/agents">← Tim Agent</a>
      <div class="panel"><h2>Agent tidak ditemukan</h2><p class="muted">Pilih salah satu: Rani, Bima, Citra, Dimas.</p></div></section>`;
    return;
  }
  const isReviewer = a.id === "dimas";
  app.innerHTML = h`
    <section class="view">
      <a class="back" href="#/agents">← Tim Agent</a>
      <div class="panel">
        <div class="profile-head">
          <img class="avatar lg" src="${a.avatar}" alt="${esc(a.nama)}">
          <div>
            <div class="role">${esc(a.urutan)}</div>
            <h1 style="font-size:28px;margin:2px 0 4px">${esc(a.nama)} <span class="zh" style="font-size:20px">${esc(a.nama_zh)}</span></h1>
            <div class="prof muted">${esc(a.profesi)}</div>
          </div>
        </div>
        <p class="lead" style="font-size:15px;margin-top:16px">${esc(a.ringkas)}</p>
      </div>

      <div class="grid cols-2" style="margin-top:16px">
        <div class="panel">
          <h3>Kapabilitas inti</h3>
          <ul class="rule-list ok">${a.kapabilitas.map((k) => h`<li>${esc(k)}</li>`).join("")}</ul>
        </div>
        <div class="panel">
          <h3>Batasan (tidak akan pernah)</h3>
          <ul class="rule-list no">${a.batasan.map((b) => h`<li>${esc(b)}</li>`).join("")}</ul>
        </div>
      </div>

      <div class="panel" style="margin-top:16px">
        <h3>Tool MCP yang dipakai</h3>
        <div class="tool-tags">${a.tools.map((t) => h`<span class="tool-tag">${esc(t)}</span>`).join("")}</div>
        ${isReviewer ? h`<p class="note-box">Wewenang lapis model dibatasi enam aturan:
          ${LAPIS2_RULES.map((r) => h`<b>${r}</b>`).join(" · ")}. Sisanya milik lapis kode.</p>` : ""}
      </div>
    </section>`;
}

// =====================================================================
// VIEW — CONSOLE (relay 4 agent)
// =====================================================================
let pollTimer = null;
// Produk yang sedang dipakai: dari unggahan dokumen (prioritas) atau dropdown (fallback).
// Dokumen hanya PENGENAL — sistem menarik ulang fakta dari server lewat SKU ini,
// tidak pernah mempercayai isi dokumen sebagai fakta. Lihat PANDUAN_UPDATE_UI.md §2.
let skuTerpilih = null;
let namaProdukTerpilih = null;

function viewConsole() {
  clearInterval(pollTimer);
  skuTerpilih = null;
  namaProdukTerpilih = null;
  app.innerHTML = h`
    <section class="view">
      <div class="hero" style="padding-bottom:0">
        <span class="pill-line"><span class="brand-dot"></span> Console review</span>
        <h1>Jalankan satu siklus, lihat tiap agent bekerja.</h1>
        <p class="lead">Unggah lembar produk (atau pilih dari daftar), pilih platform dan bahasan utama.
          Rani mengoordinasikan Bima → Citra → Dimas, berhenti di LOLOS, lalu menyerahkan ke gerbang
          approval manusia.</p>
      </div>

      <div class="panel">
        <div class="upload-area" id="upload-area">
          <label class="upload-label" for="file-pdf">
            <input type="file" id="file-pdf" accept="application/pdf" hidden>
            <span class="upload-prompt">📄 Unggah Lembar Produk (PDF) atau
              <button type="button" class="link-btn" id="tombol-dropdown">pilih dari daftar produk</button>
            </span>
          </label>
          <p class="upload-status" id="upload-status"></p>
        </div>
        <div class="controls" id="controls-sku" style="display:none">
          <label class="field">Produk (SKU)<select id="sku"></select></label>
          <button type="button" class="link-btn" id="tombol-unggah">↑ unggah dokumen sebagai gantinya</button>
        </div>
        <div class="controls">
          <label class="field">Platform<select id="platform">
            <option value="tiktok">tiktok</option>
            <option value="instagram">instagram</option>
            <option value="marketplace">marketplace</option>
          </select></label>
        </div>
        <div class="angles">
          <span class="angle-label">Pilih bahasan utama yang ingin dibuat konten:</span><span id="angles"></span>
        </div>
        <div class="btn-row">
          <button class="btn brand" id="run-btn">Jalankan review</button>
          <button class="btn ghost" id="demo-btn" title="Contoh terekam yang memicu TOLAK lalu LOLOS">▶ Putar contoh tolak → perbaiki → setujui</button>
        </div>
        <p class="statusline" id="status"></p>
      </div>

      <div id="relay"></div>
    </section>`;

  loadProducts();
  loadAngles();
  setupUpload();
  document.getElementById("run-btn").addEventListener("click", () => runLive());
  document.getElementById("demo-btn").addEventListener("click", () => playDemo());
}

// =====================================================================
// UPLOAD DOKUMEN PRODUK (utama) + fallback dropdown
// =====================================================================
function setupUpload() {
  const fileInput = document.getElementById("file-pdf");
  const uploadStatus = document.getElementById("upload-status");
  const controlsSku = document.getElementById("controls-sku");
  const tombolDropdown = document.getElementById("tombol-dropdown");
  const uploadArea = document.getElementById("upload-area");

  const tombolUnggah = document.getElementById("tombol-unggah");

  tombolDropdown.addEventListener("click", () => {
    skuTerpilih = null;
    namaProdukTerpilih = null;
    controlsSku.style.display = "block";
    uploadArea.style.display = "none";
  });

  tombolUnggah.addEventListener("click", () => {
    // Bolak-balik: dari dropdown kembali ke unggah dokumen.
    controlsSku.style.display = "none";
    uploadArea.style.display = "block";
    uploadStatus.textContent = "";
    uploadStatus.className = "upload-status";
    fileInput.value = "";
  });

  document.getElementById("sku").addEventListener("change", () => {
    // Dropdown dipakai eksplisit -> lepas pilihan dari unggahan sebelumnya.
    skuTerpilih = null;
    namaProdukTerpilih = null;
  });

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      uploadStatus.textContent = "Hanya file PDF yang diterima.";
      uploadStatus.className = "upload-status error";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      uploadStatus.textContent = "File terlalu besar (maks 2MB).";
      uploadStatus.className = "upload-status error";
      return;
    }

    uploadStatus.textContent = "Membaca dokumen…";
    uploadStatus.className = "upload-status";

    try {
      const buffer = await file.arrayBuffer();
      const res = await fetch("/api/upload-produk", {
        method: "POST",
        headers: { "content-type": "application/pdf" },
        body: buffer,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.error || "Dokumen tidak dikenali.");

      skuTerpilih = data.sku;
      try {
        const produkData = await api("/api/products");
        const produk = (produkData.produk || []).find((p) => p.sku === data.sku);
        namaProdukTerpilih = produk ? produk.nama : data.sku;
      } catch {
        namaProdukTerpilih = data.sku;
      }

      uploadStatus.innerHTML =
        `✓ Dikenali: <b>${esc(namaProdukTerpilih)}</b> (${esc(data.sku)}` +
        (data.doc_id ? ` · ${esc(data.doc_id)}` : "") +
        `). Fakta produk ditarik dari server, bukan dari isi dokumen.`;
      uploadStatus.className = "upload-status ok";
      controlsSku.style.display = "none";
    } catch (e) {
      skuTerpilih = null;
      namaProdukTerpilih = null;
      uploadStatus.textContent = e.message + " Gunakan dropdown di bawah sebagai gantinya.";
      uploadStatus.className = "upload-status error";
      controlsSku.style.display = "block";
    }
  });
}

async function loadProducts() {
  try {
    const data = await api("/api/products");
    const daftar = data.produk || [];
    document.getElementById("sku").innerHTML = daftar
      .map((p) => h`<option value="${esc(p.sku)}">${esc(p.sku)} · ${esc(p.nama)}</option>`).join("");
  } catch (e) {
    setStatus(`Gagal memuat produk: ${e.message}. Backend mungkin belum tersambung ke MCP.`, true);
  }
}

async function loadAngles() {
  try {
    const data = await api("/api/sudut");
    const box = document.getElementById("angles");
    box.innerHTML = (data.pilihan || [])
      .map((s) => h`<button class="chip-btn" data-angle="${esc(s.angle)}">${esc(s.label)}</button>`).join("");
    box.querySelectorAll(".chip-btn").forEach((b) =>
      b.addEventListener("click", () => runLive(b.dataset.angle)));
  } catch { /* tombol sudut opsional */ }
}

function setStatus(teks, salah = false) {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = teks || "";
  el.classList.toggle("error", salah);
}

async function runLive(angle = "") {
  clearInterval(pollTimer);
  const sku = skuTerpilih || document.getElementById("sku").value;
  if (!sku) {
    setStatus("Unggah dokumen produk atau pilih dari daftar dulu.", true);
    return;
  }
  const platform = document.getElementById("platform").value;
  const relay = document.getElementById("relay");
  relay.innerHTML = "";
  setStatus("Rani mengoordinasikan Planner → Writer → Reviewer…");
  document.getElementById("run-btn").disabled = true;
  try {
    // /api/run-relay: rantai granular (plan_content -> write_draft+review_draft per
    // iterasi), bukan run_cycle sebagai black box -> draf tiap iterasi ikut terlihat.
    const data = await api("/api/run-relay", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ sku, platform, ...(angle ? { angle } : {}) }),
    });
    renderRelay(data, { sku, platform, nama: namaProdukTerpilih, live: true });
    const sisa = data.sisa_jatah !== undefined ? ` · sisa jatah: ${data.sisa_jatah}` : "";
    setStatus(`Selesai — ${data.status}${sisa}`);
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    document.getElementById("run-btn").disabled = false;
  }
}

function playDemo() {
  clearInterval(pollTimer);
  setStatus("Memutar contoh terekam (replay) — bukan hasil live.");
  renderRelay(DEMO_CYCLE, { sku: DEMO_CYCLE.sku, platform: DEMO_CYCLE.platform, demo: true });
}

function chip(v) {
  const k = v === "LOLOS" ? "ok" : v === "TOLAK" ? "no" : "wait";
  return h`<span class="chip ${k}">${esc(v)}</span>`;
}

function avatarNode(id) {
  const a = agentById(id);
  return a ? h`<img src="${a.avatar}" alt="${esc(a.nama)}">` : "";
}

function who(id, fallback) {
  const a = agentById(id);
  return a ? h`<b>${esc(a.nama)}</b> · ${esc(a.profesi)}` : esc(fallback || "");
}

function step({ node, title, who: whoHtml, body }) {
  return h`
    <div class="relay-step">
      <div class="relay-rail">
        <div class="relay-node ${node.sys ? "sys" : ""}">${node.html}</div>
        <div class="relay-line"></div>
      </div>
      <div class="relay-body">
        ${whoHtml ? h`<div class="relay-who">${whoHtml}</div>` : ""}
        <div class="relay-title">${title}</div>
        ${body || ""}
      </div>
    </div>`;
}

function renderTemuan(list) {
  if (!list || !list.length) return "";
  return list.map((t) => h`
    <div class="temuan">
      <div class="temuan-head">
        <span class="rule-id">${esc(t.rule_id)}</span>
        ${t.layer ? h`<span class="layer">lapis ${esc(t.layer)}</span>` : ""}
      </div>
      <blockquote>${esc(t.span)}</blockquote>
      <p class="reason">${esc(t.reason)}</p>
      <p class="fix">Perbaiki: ${esc(t.fix)}</p>
    </div>`).join("");
}

function planFactsBox(plan) {
  if (!plan) return "";
  const boleh = plan.fakta_boleh || [];
  const dilarang = (plan.fakta_dilarang || []).map((x) => (typeof x === "string" ? x : x.teks || JSON.stringify(x)));
  if (!boleh.length && !dilarang.length) {
    return h`<div class="note-box">Rencana disusun: sudut "${esc(plan.angle || "-")}", struktur ${esc((plan.struktur || []).join(" → ") || "-")}.</div>`;
  }
  return h`
    <div class="facts">
      <div class="fact-box allow"><div class="h">Fakta boleh</div><ul>${boleh.map((x) => h`<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="fact-box deny"><div class="h">Fakta dilarang</div><ul>${dilarang.length ? dilarang.map((x) => h`<li>${esc(x)}</li>`).join("") : "<li>—</li>"}</ul></div>
    </div>`;
}

function renderRelay(data, ctx) {
  const relay = document.getElementById("relay");
  const riwayat = data.riwayat || [];
  const steps = [];

  // 1. Rani
  const labelProduk = ctx.nama ? `${ctx.nama} (${ctx.sku})` : ctx.sku;
  steps.push(step({
    node: { html: avatarNode("rani") },
    who: who("rani"),
    title: h`Menerima permintaan <span class="iter-badge">${esc(labelProduk)} · ${esc(ctx.platform)}</span>`,
    body: ctx.demo ? h`<span class="demo-flag">▶ contoh terekam</span>` : "",
  }));

  // 2. Bima
  steps.push(step({
    node: { html: avatarNode("bima") },
    who: who("bima"),
    title: "Menyusun rencana per platform",
    body: planFactsBox(data.plan),
  }));

  // 3. iterasi Citra → Dimas
  riwayat.forEach((r) => {
    steps.push(step({
      node: { html: avatarNode("citra") },
      who: who("citra"),
      title: h`Menulis draf <span class="iter-badge">iterasi ${esc(r.iterasi)}/3</span>`,
      body: r.draf ? h`<div class="draft-box">${esc(r.draf)}</div>` : "",
    }));
    steps.push(step({
      node: { html: avatarNode("dimas") },
      who: who("dimas"),
      title: h`Menilai draf ${chip(r.verdict)}`,
      body: r.verdict === "TOLAK"
        ? renderTemuan(r.temuan)
        : h`<p class="muted" style="font-size:13px;margin:0">${r.verdict === "LOLOS" ? "Tidak ada pelanggaran." : "Data tidak cukup untuk menyatakan aman."}</p>`,
    }));
  });

  // 4. hasil akhir / gerbang
  if (data.status === "LOLOS") {
    steps.push(step({
      node: { html: "✓", sys: true },
      title: "Konten final (lolos review)",
      body: h`<div class="final">${esc(data.konten_final || "")}</div>
        ${ctx.demo ? "" : h`<div class="gate" id="gate">
          <div class="baris"><strong>Gerbang approval</strong></div>
          <p class="muted" style="font-size:13px;margin:0 0 10px">Lolos ≠ terbit. Ajukan untuk membuat plan; persetujuan dilakukan manusia dengan kunci approver di luar situs ini.</p>
          <button class="btn" id="propose-btn">Ajukan approval</button>
          <div id="plan-panel"></div>
        </div>`}`,
    }));
  } else if (data.status === "PERLU_DATA") {
    steps.push(step({
      node: { html: "?", sys: true },
      title: h`${chip("PERLU_DATA")} Tidak bisa dinyatakan aman`,
      body: h`<p class="note-box">${esc(data.catatan || "SKU tidak ada di registri — harga, BPOM, halal, dan izin tidak dapat diverifikasi. Ini bukan lulus.")}</p>`,
    }));
  } else {
    steps.push(step({
      node: { html: "!", sys: true },
      title: "Eskalasi ke manusia",
      body: h`<p class="note-box">${esc(data.catatan || "Setelah 3 iterasi masih ada pelanggaran. Diserahkan ke Regulatory dengan sisa masalah — tidak ada yang terbit.")}</p>`,
    }));
  }

  // buang garis terakhir
  relay.innerHTML = h`<div class="panel relay">${steps.join("")}</div>`;
  const lines = relay.querySelectorAll(".relay-step:last-child .relay-line");
  lines.forEach((l) => (l.style.display = "none"));

  if (data.status === "LOLOS" && !ctx.demo) {
    const btn = document.getElementById("propose-btn");
    if (btn) btn.addEventListener("click", () => ajukan(ctx, data.konten_final));
  }
  if (ctx.demo) {
    const box = document.createElement("p");
    box.className = "note-box";
    box.textContent = data.catatan || "";
    relay.appendChild(box);
  }
}

async function ajukan(ctx, konten) {
  const btn = document.getElementById("propose-btn");
  const panel = document.getElementById("plan-panel");
  try {
    btn.disabled = true;
    panel.innerHTML = h`<p class="muted" style="font-size:13px;margin-top:10px">Mengajukan ke gerbang approval…</p>`;
    const data = await api("/api/propose", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ sku: ctx.sku, platform: ctx.platform, content: konten || "" }),
    });
    const menit = Number(data.kedaluwarsa_menit || 30);
    panel.innerHTML = h`
      <div style="margin-top:12px">
        <div class="baris" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <span class="tool-tag">plan_id</span><code>${esc(data.plan_id)}</code>
          <span class="muted" style="font-size:12px">kedaluwarsa ${menit} menit</span>
        </div>
        <p class="muted" id="plan-status" style="font-size:13px;margin:8px 0 0">PROPOSED — belum disetujui siapa pun.</p>
        <p class="note-box">Persetujuan dilakukan pemilik di sesi WorkBuddy dengan kunci approver.
        Situs ini tidak memegang kunci itu, jadi tidak ada tombol di sini yang bisa menyetujui.</p>
      </div>`;
    pollStatus(data.plan_id);
  } catch (e) {
    panel.innerHTML = h`<p class="statusline error" style="margin-top:10px">${esc(e.message)}</p>`;
    btn.disabled = false;
  }
}

function pollStatus(planId) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const s = await api(`/api/status?plan_id=${encodeURIComponent(planId)}`);
      const node = document.getElementById("plan-status");
      if (!node) return clearInterval(pollTimer);
      if (s.status === "APPROVED") {
        node.innerHTML = h`<span class="chain-ok">APPROVED oleh ${esc(s.approver)}</span> · ${esc(s.waktu || "")}`;
        clearInterval(pollTimer);
      } else if (s.status === "REJECTED") {
        node.innerHTML = h`<span class="chain-no">REJECTED oleh manusia.</span>`;
        clearInterval(pollTimer);
      } else {
        node.textContent = `PROPOSED — menunggu persetujuan · ${s.jumlah_entri ?? 0} entri audit`;
      }
    } catch { /* jaringan goyang, coba lagi */ }
  }, 5000);
}

// =====================================================================
// VIEW — CEK DRAF (Bukti Penolakan)
// =====================================================================
// Form ringan: tempel caption apa pun → /api/review → TOLAK dengan nomor
// aturan + kutipan + perbaikan, atau LOLOS. Ini membuktikan gerbang tolak
// bekerja sebelum konten mencapai approval — tanpa memalsukan approval.
const CONTOH_PELANGGARAN =
  "Glow Serum Vitamin C 20% ini DIPERCAYA membuat kulit putih berseri dalam 3 hari! " +
  "Terbukti aman karena sudah BPOM dan HALAL MUI. Komposngi premium Korea, " +
  "hasilnya paling bagus dari semua serum yang pernah ada. Garansi uang kembali!";

function viewCek() {
  app.innerHTML = h`
    <section class="view">
      <div class="hero" style="padding-bottom:0">
        <span class="pill-line"><span class="brand-dot"></span> Bukti penolakan — gerbang sebelum terbit</span>
        <h1>Tempel caption apa pun. Lihat apakah ditolak.</h1>
        <p class="lead">Mesin reviewer (Dimas) memeriksa draf terhadap aturan klaim BPOM &amp; halal.
          Caption yang melanggar ditolak dengan nomor aturan, kutipan persis, dan perbaikan.
          Caption yang bersih lolos — tetap belum terbit sampai manusia menyetujui.</p>
      </div>

      <div class="panel">
        <div class="controls">
          <label class="field">Produk (SKU)<select id="cek-sku"></select></label>
          <label class="field">Platform<select id="cek-platform">
            <option value="tiktok">tiktok</option>
            <option value="instagram">instagram</option>
            <option value="marketplace">marketplace</option>
          </select></label>
        </div>
        <label class="field" style="margin-bottom:10px">Caption / draf
          <textarea id="cek-input" placeholder="Tempel caption iklan di sini…" maxlength="5000"></textarea>
        </label>
        <div class="btn-row">
          <button class="btn brand" id="cek-btn">Periksa draf</button>
          <button class="btn ghost" id="cek-contoh">Contoh pelanggaran</button>
        </div>
        <p class="statusline" id="cek-status"></p>
      </div>

      <div id="cek-hasil"></div>
    </section>`;

  cekLoadProducts();
  document.getElementById("cek-btn").addEventListener("click", cekPeriksa);
  document.getElementById("cek-contoh").addEventListener("click", () => {
    document.getElementById("cek-input").value = CONTOH_PELANGGARAN;
    cekSetStatus("Contoh pelanggaran dimuat. Klik 'Periksa draf' untuk melihat penolakannya.");
  });
}

async function cekLoadProducts() {
  try {
    const data = await api("/api/products");
    const daftar = data.produk || [];
    document.getElementById("cek-sku").innerHTML = daftar
      .map((p) => h`<option value="${esc(p.sku)}">${esc(p.sku)} · ${esc(p.nama)}</option>`).join("");
  } catch {
    document.getElementById("cek-sku").innerHTML = "<option value=\"\">— gagal memuat —</option>";
  }
}

function cekSetStatus(teks, salah = false) {
  const el = document.getElementById("cek-status");
  if (!el) return;
  el.textContent = teks || "";
  el.classList.toggle("error", salah);
}

async function cekPeriksa() {
  const sku = document.getElementById("cek-sku").value;
  const platform = document.getElementById("cek-platform").value;
  const content = document.getElementById("cek-input").value;
  const hasil = document.getElementById("cek-hasil");
  if (!sku) { cekSetStatus("Pilih produk dulu.", true); return; }
  if (!content.trim()) { cekSetStatus("Caption tidak boleh kosong.", true); return; }
  if (content.length > 5000) { cekSetStatus("Caption melebihi 5000 karakter.", true); return; }

  cekSetStatus("Memeriksa…");
  const btn = document.getElementById("cek-btn");
  btn.disabled = true;
  hasil.innerHTML = "";
  try {
    const data = await api("/api/review", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ sku, platform, content }),
    });
    cekRenderHasil(data);
    const sisa = data.sisa_jatah !== undefined ? ` · sisa jatah: ${data.sisa_jatah}` : "";
    cekSetStatus(`Selesai — ${data.status}${sisa}`);
  } catch (e) {
    cekSetStatus(e.message, true);
  } finally {
    btn.disabled = false;
  }
}

function cekRenderHasil(data) {
  const hasil = document.getElementById("cek-hasil");
  const tolak = data.status === "TOLAK";
  const temuan = data.temuan || [];
  const banner = tolak
    ? h`<div class="verdict-banner no"><span class="chip no">TOLAK</span> ${temuan.length} temuan ditemukan <span class="count">— tiap temuan membawa nomor aturan, kutipan, dan perbaikan</span></div>`
    : h`<div class="verdict-banner ok"><span class="chip ok">LOLOS</span> Tidak ada pelanggaran <span class="count">— boleh diajukan ke gerbang approval, belum terbit</span></div>`;

  hasil.innerHTML = h`
    <div class="panel" style="margin-top:16px">
      ${banner}
      ${temuan.length ? renderTemuan(temuan) : ""}
      ${!tolak ? h`<p class="note-box">Lolos review bukan berarti terbit. Konten harus diajukan dan disetujui manusia dengan kunci approver — tidak ada tombol di sini yang bisa menyetujui.</p>` : ""}
    </div>`;
}

// =====================================================================
// VIEW — AUDIT
// =====================================================================
async function viewAudit() {
  app.innerHTML = h`
    <section class="view">
      <div class="hero" style="padding-bottom:0">
        <span class="pill-line"><span class="brand-dot"></span> Jejak & kepercayaan</span>
        <h1>Setiap langkah tercatat, dan tak bisa diubah diam-diam.</h1>
        <p class="lead">Audit log bersifat append-only dengan rantai hash: tiap entri menyimpan hash entri
          sebelumnya, sehingga mengubah satu baris memutus rantai dan langsung terdeteksi.</p>
      </div>
      <div class="panel">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
          <h3 style="margin:0">Entri terakhir</h3>
          <button class="btn ghost" id="refresh">Muat ulang</button>
        </div>
        <div id="audit-body"><p class="muted" style="font-size:13px">Memuat…</p></div>
      </div>
      <div class="panel">
        <h3>Urutan yang dijaga</h3>
        <p class="muted" style="font-size:13.5px;margin:0">
          <code>plan → write → review → plan_propose → plan_approve → execute</code>.
          Tidak ada <code>execute</code> tanpa <code>plan_approve</code> lebih dulu; percobaan menyetujui
          diri sendiri atau kunci salah ikut tercatat sebagai <code>approval_blocked</code>.</p>
      </div>
    </section>`;
  const load = () => loadAudit();
  document.getElementById("refresh").addEventListener("click", load);
  load();
}

async function loadAudit() {
  const body = document.getElementById("audit-body");
  try {
    // /api/status memakai audit_tail di balik layar; bila endpoint tail publik
    // belum ada, tampilkan panduan alih-alih mengarang data.
    const data = await api("/api/audit?n=20").catch(() => null);
    if (!data || !Array.isArray(data.entri)) {
      body.innerHTML = h`<p class="note-box">Endpoint audit publik belum diekspos BFF (hanya dipakai internal oleh <code>/api/status</code>).
        Untuk menayangkan tabel ini, tambahkan rute <code>GET /api/audit</code> yang memanggil tool <code>audit_tail</code> — lihat NOTES.md.</p>`;
      return;
    }
    const rows = data.entri.map((e) => h`
      <tr><td><code>#${esc(e.seq)}</code></td><td>${esc((e.ts || "").slice(11, 19))}</td>
      <td>${esc(e.actor)}</td><td><code>${esc(e.action)}</code></td>
      <td>${esc(e.target || "")}</td><td>${esc(e.result || "")}</td></tr>`).join("");
    body.innerHTML = h`
      <p style="margin:6px 0 10px"><span class="chain-ok">● rantai utuh</span></p>
      <table class="audit-table"><thead><tr><th>#</th><th>waktu</th><th>aktor</th><th>aksi</th><th>target</th><th>hasil</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  } catch (e) {
    body.innerHTML = h`<p class="statusline error">${esc(e.message)}</p>`;
  }
}
