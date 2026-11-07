// upload-produk.route.js — TEMPEL ke web/server/index.js (bukan file yang di-import).
//
// Cara pasang:
//   1. Tambah `import { PDFParse } from "pdf-parse";` di bagian import atas index.js.
//   2. Tambah `upload: { maks: 10, jendela: 60 * 60 * 1000 },` ke objek BATAS.
//   3. Tempel blok "if (...)" di bawah ini ke dalam fungsi tanganiApi(), SEBELUM baris
//      `return kirim(res, 404, { error: "tidak ada" });` di akhir fungsi.
//
// TERVERIFIKASI: diuji nyata terhadap 4 PDF di dataset_c/product_profile_pdf/
// dengan `node backend-patch/test-pdf-extract.mjs` — regex & API pdf-parse v2 cocok.
//
// PRINSIP WAJIB (lihat PANDUAN_UPDATE_UI.md §2): dokumen hanya PENGENAL SKU.
// Endpoint ini TIDAK PERNAH membaca harga/klaim/komposisi dari isi PDF sebagai fakta —
// hanya SKU untuk lookup ulang ke list_products (data resmi server).

if (req.method === "POST" && url.pathname === "/api/upload-produk") {
  const jatah = boleh(ip, "upload");
  if (!jatah.ok) {
    return kirim(res, 429, {
      error: `Batas unggah tercapai. Coba lagi dalam ${jatah.detik} detik.`,
    });
  }

  // Baca body sebagai buffer biner (bukan JSON) — bacaJson() tidak cocok untuk PDF.
  let ukuran = 0;
  const potong = [];
  for await (const bagian of req) {
    ukuran += bagian.length;
    if (ukuran > 2 * 1024 * 1024) {
      return kirim(res, 413, { error: "file terlalu besar (maks 2MB)" });
    }
    potong.push(bagian);
  }
  if (!potong.length) {
    return kirim(res, 400, { error: "berkas kosong" });
  }
  const buffer = Buffer.concat(potong);

  // Ekstrak teks PDF. pdf-parse v2 memakai API class (BUKAN pdfParse(buffer) lama).
  let teks = "";
  try {
    const parser = new PDFParse({ data: buffer });
    const hasil = await parser.getText();
    teks = hasil.text || "";
    await parser.destroy();
  } catch {
    return kirim(res, 400, {
      ok: false,
      error: "Berkas tidak bisa dibaca sebagai PDF. Gunakan dropdown sebagai gantinya.",
    });
  }

  // Field metadata ada di header dokumen (lihat dataset_c/product_profile_pdf/*.pdf §header).
  // Toleran spasi/baris baru karena PDF menata teks per sel tabel, bukan satu baris.
  const cocokSku = teks.match(/SKU[\s\n]+(AY-[A-Z]{2}-\d{3})/);
  if (!cocokSku) {
    return kirim(res, 400, {
      ok: false,
      error: "SKU tidak ditemukan di dokumen. Gunakan dropdown sebagai gantinya.",
    });
  }
  const sku = cocokSku[1];

  // Validasi ke registri sungguhan — TIDAK pernah mempercayai field lain dari PDF.
  const produkData = await klien.panggilTool("list_products", {});
  const dikenal = (produkData.produk || []).some((p) => p.sku === sku);
  if (!dikenal) {
    return kirim(res, 400, {
      ok: false,
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
