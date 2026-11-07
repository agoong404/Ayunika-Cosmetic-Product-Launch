// run-relay.route.js — TEMPEL ke web/server/index.js, GANTI atau DAMPINGI /api/run.
//
// Kenapa: run_cycle() di mcp_server/tools.py (dipanggil /api/run yang ada) TIDAK
// menyimpan teks draf per iterasi di `riwayat` — hanya verdict + temuan. Jadi UI tidak
// bisa menampilkan "Citra menulis apa". Dicek langsung di tools.py:472-483 (7 Nov 2026).
//
// Endpoint ini memanggil 3 tool yang SAMA PERSIS dipanggil run_cycle() secara internal
// (plan_content -> write_draft -> loop review_draft/write_draft) — TIDAK ada perubahan
// di mcp_server/ atau engine/. Hanya "membuka" apa yang run_cycle sembunyikan.
//
// Cara pasang: tempel blok "if (...)" di bawah ke dalam tanganiApi(), di dekat /api/run
// yang sudah ada. Boleh menambah endpoint baru (/api/run-relay) atau mengganti isi
// /api/run — ayunika-ui/public/app.js versi baru memanggil /api/run-relay.

if (req.method === "POST" && url.pathname === "/api/run-relay") {
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

  // 1. Bima — rencana
  const rencana = await klien.panggilTool("plan_content", {
    sku: body.sku,
    platform: body.platform,
    ...(angle ? { angle } : {}),
  });
  if (!rencana.ok) {
    return kirim(res, 200, { ...rencana, sisa_jatah: jatah.sisa });
  }
  const plan = rencana.plan;

  // 2+3. Citra (write_draft) <-> Dimas (review_draft), maks 3 iterasi — identik
  // dengan loop di mcp_server/tools.py:run_cycle(), hanya disimpan draf-nya juga.
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
}
