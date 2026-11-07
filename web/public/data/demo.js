// demo.js — satu siklus tolak → perbaiki → setujui untuk "mode replay".
//
// KENAPA ADA: Writer deterministik di jalur live bersifat konservatif dan
// hampir selalu LOLOS di iterasi pertama, sehingga pengunjung jarang melihat
// siklus perbaikan — padahal itu syarat wajib Challenge C. Replay ini
// memperlihatkan siklus penuh tanpa mengarang: isinya diambil dari pola
// DRAFT-101 v1→v2 dan aturan R-01/R-07 di rulebook repo.
//
// Tandai jelas di UI sebagai "contoh terekam", bukan hasil live.

export const DEMO_CYCLE = {
  sku: "AY-SR-101",
  produk: "Ayunika Bright Serum",
  platform: "tiktok",
  status: "LOLOS",
  sumber: "replay",
  riwayat: [
    {
      iterasi: 1,
      verdict: "TOLAK",
      draf:
        "WOW!!! Serum ajaib ini menyembuhkan jerawat dalam 7 hari, dijamin! " +
        "Kulit langsung glowing seketika. Buruan sebelum kehabisan!",
      temuan: [
        {
          rule_id: "R-01",
          layer: "kode",
          span: "menyembuhkan jerawat",
          reason:
            "Kosmetik dilarang mengklaim menyembuhkan/mengobati penyakit atau kondisi kulit.",
          fix: "Ganti dengan manfaat yang diizinkan: 'membantu merawat kulit berjerawat'.",
        },
        {
          rule_id: "R-07",
          layer: "kode",
          span: "dalam 7 hari, dijamin",
          reason:
            "Janji hasil berjangka waktu dan kata 'dijamin' adalah superlatif terlarang.",
          fix: "Hapus janji waktu dan jaminan. Nyatakan cara kerja, bukan hasil pasti.",
        },
        {
          rule_id: "R-07",
          layer: "model",
          span: "seketika",
          reason: "'Seketika' adalah janji hasil instan yang menyesatkan.",
          fix: "Gunakan bahasa berhati-hati: 'membantu menyegarkan tampilan kulit'.",
        },
      ],
    },
    {
      iterasi: 2,
      verdict: "TOLAK",
      draf:
        "Serum ajaib dengan niacinamide 5% untuk kulit kusam. " +
        "Membantu mencerahkan tampilan kulit. Cek keranjang kuning ya. " +
        "Hasil dapat berbeda pada setiap orang.",
      temuan: [
        {
          rule_id: "R-07",
          layer: "model",
          span: "ajaib",
          reason: "'Ajaib' adalah klaim keajaiban yang tidak dapat dibuktikan.",
          fix: "Hapus 'ajaib'. Sebut kandungan dan kegunaannya secara lugas.",
        },
      ],
    },
    {
      iterasi: 3,
      verdict: "LOLOS",
      draf:
        "Serum dengan niacinamide 5% untuk kulit kusam. " +
        "Membantu mencerahkan tampilan kulit, tekstur ringan dan cepat meresap. " +
        "Cek keranjang kuning ya. Hasil dapat berbeda pada setiap orang.",
      temuan: [],
    },
  ],
  konten_final:
    "Serum dengan niacinamide 5% untuk kulit kusam. " +
    "Membantu mencerahkan tampilan kulit, tekstur ringan dan cepat meresap. " +
    "Cek keranjang kuning ya. Hasil dapat berbeda pada setiap orang.",
  catatan:
    "Contoh terekam (replay) dari pola DRAFT-101. Pada jalur live, Writer " +
    "deterministik cenderung lolos di iterasi 1. Replay ini memperlihatkan " +
    "siklus tolak → perbaiki → setujui secara utuh.",
};
