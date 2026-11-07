// test-pdf-extract.mjs — verifikasi regex ekstraksi SKU/doc_id dari PDF Lembar Produk.
// Jalankan: node backend-patch/test-pdf-extract.mjs
// Bukan bagian dari runtime BFF — alat verifikasi sekali pakai untuk developer.
import { readFile, readdir } from "node:fs/promises";
import { PDFParse } from "pdf-parse";

const DIR = "../../../dataset_c/product_profile_pdf";
const SKU_RE = /SKU[\s\n]+(AY-[A-Z]{2}-\d{3})/;
const DOC_RE = /No\.\s*Dokumen[\s\n]+(PS-\d{3})/i;

const files = (await readdir(new URL(DIR, import.meta.url))).filter((f) => f.endsWith(".pdf"));
if (!files.length) {
  console.error("Tidak ada PDF ditemukan di", DIR);
  process.exit(1);
}

let gagal = 0;
for (const f of files) {
  const buf = await readFile(new URL(`${DIR}/${f}`, import.meta.url));
  const parser = new PDFParse({ data: buf });
  const data = await parser.getText();
  await parser.destroy();
  const sku = data.text.match(SKU_RE);
  const doc = data.text.match(DOC_RE);
  const ok = sku && doc;
  if (!ok) gagal++;
  console.log(
    `${ok ? "OK  " : "GAGAL"} ${f} -> sku=${sku ? sku[1] : "?"} doc_id=${doc ? doc[1] : "?"}`
  );
}
console.log(gagal ? `\n${gagal} file GAGAL diparse — regex perlu diperbaiki.` : "\nSemua file cocok.");
process.exit(gagal ? 1 : 0);
