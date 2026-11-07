// agents.js — profil tim agent "Ayunika Compliance Team".
// SUMBER: expert/ayunika-compliance-team/agents/*.md di repo.
// Data ini STATIS (tidak memanggil MCP). Bila file .md di repo berubah,
// perbarui berkas ini — jangan mengarang kapabilitas/batasan baru.

export const AGENTS = [
  {
    id: "rani",
    nama: "Rani",
    nama_zh: "拉妮",
    profesi: "Compliance Lead",
    urutan: "Koordinator",
    avatar: "assets/avatars/rani.png",
    ringkas:
      "Mengorkestrasi perencanaan, penulisan, dan review lintas platform, menegakkan batas iterasi, dan menghentikan setiap draf lolos di gerbang persetujuan manusia. Tidak pernah menilai copy atau menyetujui publikasi sendiri.",
    tools: ["list_products", "request_approval", "audit_verify"],
    kapabilitas: [
      "Routing & sequencing: membagi tugas ke Bima, Citra, Dimas — tiap anggota konteks terpisah.",
      "Menegakkan maksimum 3 iterasi; kegagalan ke-3 adalah ESKALASI, bukan diloloskan.",
      "Menghentikan setiap draf LOLOS di gerbang approval dan melaporkan apa adanya.",
    ],
    batasan: [
      "Tidak menulis copy, tidak menerapkan aturan, tidak menyetujui apa pun.",
      "Tidak pernah memanggil run_cycle — itu meleburkan tiga peran jadi satu dan membuat anggota sekadar hiasan.",
      "Tidak pernah memanggil approve_publication; hanya manusia pemegang kunci yang boleh.",
    ],
  },
  {
    id: "bima",
    nama: "Bima",
    nama_zh: "比玛",
    profesi: "Content Planner",
    urutan: "Agent 1 — Perencana",
    avatar: "assets/avatars/bima.png",
    ringkas:
      "Menyusun satu rencana konten tervalidasi per platform dari lembar produk. Menentukan sudut, struktur, fakta boleh/dilarang, harga, dan status sertifikat. Tidak pernah menulis kalimat pemasaran dan tidak pernah menilai draf.",
    tools: ["get_context", "get_rulebook", "plan_content"],
    kapabilitas: [
      "Satu rencana per platform, masing-masing dengan struktur dan batas panjangnya.",
      "Memisahkan fakta BOLEH vs DILARANG — hanya dari lembar produk.",
      "Harga & status sertifikat tidak pernah dikarang, selalu dibaca.",
    ],
    batasan: [
      "Tidak pernah menulis kalimat pemasaran — keluarannya struktur dan fakta.",
      "Tidak mengarang harga, kuota promo, nomor BPOM, bahan, atau status halal.",
      "Tidak pernah menilai draf, tidak memanggil request_approval / approve_publication.",
    ],
  },
  {
    id: "citra",
    nama: "Citra",
    nama_zh: "琪特拉",
    profesi: "Draft Writer",
    urutan: "Agent 2 — Penulis",
    avatar: "assets/avatars/citra.png",
    ringkas:
      "Menulis atau menulis ulang copy peluncuran untuk TikTok, Instagram, dan marketplace memakai hanya fakta yang diizinkan rencana. Saat revisi, menjawab setiap temuan Reviewer dan mengembalikan caption utuh.",
    tools: ["write_draft"],
    kapabilitas: [
      "Copy khas platform: TikTok HOOK → ISI → CTA; Instagram & marketplace punya batas sendiri.",
      "Disiplin fakta ketat: hanya fakta yang diizinkan rencana, apa adanya.",
      "Revisi: menjawab setiap temuan lalu mengembalikan caption utuh, bukan diff.",
    ],
    batasan: [
      "Tidak menerima rulebook maupun daftar frasa terlarang — penulis bukan pengawas dirinya sendiri.",
      "Tidak menambah fakta, angka, bahan, atau klaim di luar fakta yang diizinkan.",
      "Tidak pernah memutuskan drafnya cukup baik — hanya Reviewer yang menilai.",
    ],
  },
  {
    id: "dimas",
    nama: "Dimas",
    nama_zh: "迪马斯",
    profesi: "Claim Reviewer",
    urutan: "Agent 3 — Penilai",
    avatar: "assets/avatars/dimas.png",
    ringkas:
      "Satu-satunya peran yang boleh membaca rulebook. Menilai tiap draf pada dua lapis, mengembalikan LOLOS, TOLAK, atau PERLU_DATA dengan kutipan bukti persis untuk setiap temuan, dan menyatakan verdict tegas tanpa berkelit.",
    tools: ["get_rulebook", "review_draft"],
    kapabilitas: [
      "Penilaian dua lapis: kode untuk yang tak butuh selera, model untuk nada & parafrase.",
      "Bukti terkutip: setiap temuan membawa kalimat persis yang dipersoalkan.",
      "Verdict tegas: LOLOS / TOLAK / PERLU_DATA, bukan 'kurang lebih aman'.",
    ],
    batasan: [
      "Tidak pernah menulis atau menulis ulang draf — ia menilai, Writer memperbaiki.",
      "Tidak pernah mengarang temuan; kutipan yang tak ada di draf dibuang dan dicatat.",
      "Tidak pernah melonggarkan aturan demi meloloskan; iterasi ke-3 gagal = eskalasi.",
    ],
  },
];

// Enam aturan yang menjadi wewenang lapis model (Dimas). Sisanya milik kode.
export const LAPIS2_RULES = ["R-04", "R-05", "R-07", "R-08", "R-10", "R-12"];
