// mcp.js — klien MCP minimal untuk streamable HTTP.
//
// Hanya yang dipakai situs ini: satu POST JSON-RPC, balasan JSON atau SSE.
// Tanpa SDK: satu ketergantungan lebih sedikit yang bisa rusak saat demo.

const TIMEOUT_MS = 30_000;

/** Ambil objek JSON-RPC dari balasan: JSON biasa atau baris `data:` (SSE). */
function ambilPesan(teks) {
  const bersih = teks.trim();
  if (bersih.startsWith("{")) {
    try {
      return JSON.parse(bersih);
    } catch {
      return null;
    }
  }
  for (const baris of bersih.split(/\r?\n/)) {
    if (!baris.startsWith("data:")) continue;
    try {
      return JSON.parse(baris.slice(5).trim());
    } catch {
      // baris lain dari stream, lanjut
    }
  }
  return null;
}

export function buatKlien({ url, token }) {
  let nomor = 0;

  async function panggil(method, params) {
    const badan = { jsonrpc: "2.0", id: ++nomor, method, params: params ?? {} };
    const kendali = new AbortController();
    const jam = setTimeout(() => kendali.abort(), TIMEOUT_MS);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(badan),
        signal: kendali.signal,
      });
      const teks = await res.text();
      if (!res.ok) {
        throw new Error(`MCP ${res.status}: ${teks.slice(0, 200)}`);
      }
      const pesan = ambilPesan(teks);
      if (!pesan) throw new Error("balasan MCP tidak bisa dibaca");
      if (pesan.error) {
        throw new Error(pesan.error.message || JSON.stringify(pesan.error));
      }
      return pesan.result;
    } finally {
      clearTimeout(jam);
    }
  }

  async function panggilTool(nama, argumen) {
    const hasil = await panggil("tools/call", { name: nama, arguments: argumen ?? {} });
    if (hasil?.isError) {
      const teks = (hasil.content ?? []).map((c) => c.text).join("\n") || "error";
      throw new Error(teks.slice(0, 300));
    }
    const teks = (hasil?.content ?? []).find((c) => c.type === "text")?.text;
    if (!teks) return {};
    try {
      return JSON.parse(teks);
    } catch {
      return { teks };
    }
  }

  return { panggil, panggilTool };
}
