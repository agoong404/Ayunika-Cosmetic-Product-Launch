const el = (s) => document.querySelector(s);

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);

let hasil = null;
let planId = null;
let timerPoll = null;
let timerHitung = null;

function pesan(teks, salah = false) {
  const p = el("#pesan");
  p.textContent = teks || "";
  p.classList.toggle("error", salah);
}

async function api(jalur, opsi = {}) {
  const res = await fetch(jalur, opsi);
  let data = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function muatProduk() {
  const data = await api("/api/products");
  const daftar = data.produk || [];
  el("#sku").innerHTML = daftar
    .map(
      (p) =>
        `<option value="${esc(p.sku)}">${esc(p.sku)} · ${esc(p.nama)} · ${esc(p.isi)}</option>`,
    )
    .join("");
}

let penjelasSiap = false;

async function muatKonfigurasi() {
  try {
    const data = await api("/api/config");
    penjelasSiap = Boolean(data.penjelas);
  } catch {
    penjelasSiap = false;
  }
  if (!penjelasSiap) el("#panel-tanya").hidden = true;
}

function chip(verdict) {
  const kelas = verdict === "LOLOS" ? "ok" : verdict === "TOLAK" ? "no" : "wait";
  return `<span class="chip ${kelas}">${esc(verdict)}</span>`;
}

async function ambilAturan(ids) {
  const peta = new Map();
  if (!ids.length) return peta;
  try {
    const data = await api("/api/rulebook", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    for (const a of data.aturan || []) peta.set(a.rule_id, a);
  } catch {
    // tanpa teks aturan pun temuan tetap tampil
  }
  return peta;
}

function renderTemuan(daftar, peta) {
  if (!daftar.length) return "";
  return daftar
    .map((t) => {
      const aturan = peta.get(t.rule_id);
      const teksAturan = aturan
        ? `<p class="aturan"><strong>${esc(t.rule_id)}</strong> — ${esc(aturan.teks)}</p>`
        : "";
      return `
      <div class="temuan">
        <div class="temuan-head">
          <span class="rule">${esc(t.rule_id)}</span>
          <span class="layer">lapis ${esc(t.layer)}</span>
        </div>
        ${teksAturan}
        <blockquote>${esc(t.span)}</blockquote>
        <p>${esc(t.reason)}</p>
        <p class="fix">Perbaiki: ${esc(t.fix)}</p>
      </div>`;
    })
    .join("");
}

async function renderHasil(data) {
  const riwayat = data.riwayat || [];
  const akhir = riwayat[riwayat.length - 1] || {};
  const temuan = akhir.temuan || [];
  const jejak = riwayat.map((r) => `v${r.iterasi} ${r.jumlah_temuan} temuan`).join(" → ");
  const lolos = data.status === "LOLOS";

  const ids = [...new Set(temuan.map((t) => t.rule_id))];
  const peta = await ambilAturan(ids);

  el("#hasil").innerHTML = `
    <div class="hasil-head">
      ${chip(data.status)}
      <span class="trail">${esc(jejak)}</span>
    </div>
    ${renderTemuan(temuan, peta)}
    ${
      lolos
        ? `<div class="konten">${esc(data.konten_final)}</div>
           <div class="baris" style="margin-top:14px">
             <button id="tombol-usul">Ajukan approval</button>
           </div>`
        : `<p class="note" style="margin-top:12px">${esc(data.catatan || "")}</p>`
    }
    <div id="panel-plan"></div>`;

  if (lolos) el("#tombol-usul").addEventListener("click", ajukan);

  const jawaban = el("#jawaban");
  if (jawaban) {
    jawaban.hidden = true;
    jawaban.textContent = "";
  }
  el("#panel-tanya").hidden = !penjelasSiap;
}

function renderPlan(data) {
  const menit = Number(data.kedaluwarsa_menit || 30);
  const habis = Date.now() + menit * 60_000;

  el("#panel-plan").innerHTML = `
    <div class="plan">
      <div class="baris">
        <span class="rule">plan_id</span>
        <code>${esc(data.plan_id)}</code>
        <span class="trail" id="hitung"></span>
      </div>
      <p class="trail" id="status-plan">PROPOSED — belum disetujui siapa pun.</p>
      <p class="note">Persetujuan dilakukan pemilik di sesi WorkBuddy dengan kunci
      approver. Situs ini tidak memegang kunci itu, jadi tidak ada tombol di sini
      yang bisa menyetujui.</p>
    </div>`;

  clearInterval(timerHitung);
  timerHitung = setInterval(() => {
    const sisa = Math.max(0, habis - Date.now());
    const m = Math.floor(sisa / 60_000);
    const d = Math.floor((sisa % 60_000) / 1000);
    const node = el("#hitung");
    if (node) node.textContent = `kedaluwarsa ${m}:${String(d).padStart(2, "0")}`;
    if (sisa <= 0) clearInterval(timerHitung);
  }, 1000);
}

function mulaiPolling() {
  clearInterval(timerPoll);
  timerPoll = setInterval(async () => {
    if (!planId) return;
    try {
      const s = await api(`/api/status?plan_id=${encodeURIComponent(planId)}`);
      const node = el("#status-plan");
      if (!node) return;
      if (s.status === "APPROVED") {
        node.innerHTML = `APPROVED oleh <strong>${esc(s.approver)}</strong> · ${esc(s.waktu)}`;
        pesan("Disetujui. Rantai audit bertambah satu entri.");
        clearInterval(timerPoll);
        clearInterval(timerHitung);
      } else if (s.status === "REJECTED") {
        node.textContent = "REJECTED oleh manusia.";
        clearInterval(timerPoll);
        clearInterval(timerHitung);
      } else {
        node.textContent = `PROPOSED — menunggu persetujuan · ${s.jumlah_entri} entri audit`;
      }
    } catch {
      // jaringan goyang: biarkan, coba lagi di putaran berikutnya
    }
  }, 5000);
}

async function ajukan() {
  const tombol = el("#tombol-usul");
  try {
    tombol.disabled = true;
    pesan("Mengajukan ke gerbang approval…");
    const data = await api("/api/propose", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        sku: el("#sku").value,
        platform: el("#platform").value,
        content: hasil?.konten_final || "",
      }),
    });
    planId = data.plan_id;
    pesan("Diajukan. Menunggu persetujuan manusia — bukan disetujui.");
    renderPlan(data);
    mulaiPolling();
  } catch (e) {
    pesan(e.message, true);
    if (tombol) tombol.disabled = false;
  }
}

el("#form-review").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  clearInterval(timerPoll);
  clearInterval(timerHitung);
  planId = null;

  const tombol = el("#tombol-review");
  tombol.disabled = true;
  pesan("Menjalankan Planner → Writer → Reviewer…");
  try {
    const data = await api("/api/run", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        sku: el("#sku").value,
        platform: el("#platform").value,
        angle: el("#angle").value,
      }),
    });
    hasil = data;
    await renderHasil(data);
    pesan(
      data.sisa_jatah !== undefined
        ? `Selesai. Sisa jatah review Anda: ${data.sisa_jatah}.`
        : "Selesai.",
    );
  } catch (e) {
    pesan(e.message, true);
  } finally {
    tombol.disabled = false;
  }
});

el("#form-tanya").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const tombol = el("#tombol-tanya");
  const kotak = el("#jawaban");
  const riwayat = hasil?.riwayat || [];
  const akhir = riwayat[riwayat.length - 1] || {};

  tombol.disabled = true;
  kotak.hidden = false;
  kotak.textContent = "Menjelaskan…";
  try {
    const data = await api("/api/explain", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        question: el("#tanya").value,
        verdict: hasil?.status || "",
        sku: el("#sku").value,
        temuan: akhir.temuan || [],
      }),
    });
    kotak.textContent = data.jawaban;
  } catch (e) {
    kotak.textContent = e.message;
  } finally {
    tombol.disabled = false;
  }
});

muatProduk().catch((e) => pesan(`Gagal memuat produk: ${e.message}`, true));
muatKonfigurasi();
