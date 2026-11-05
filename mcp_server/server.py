"""
server.py — pendaftaran tool ke MCPServer. Tidak ada kode transport di sini.

`stdio.py` memakai modul ini apa adanya; `http.py` (Path B) memakai objek `mcp`
yang sama. Karena itu jangan menaruh apa pun yang khusus satu transport di sini.
"""
from __future__ import annotations

from mcp.server import MCPServer

from . import tools

INSTRUCTIONS = (
    "Reviewer konten peluncuran kosmetik Ayunika. Alur yang benar: "
    "list_products → get_context → plan_content → write_draft → review_draft. "
    "review_draft mengembalikan verdict LOLOS, TOLAK, atau PERLU_DATA. "
    "PERLU_DATA bukan lulus: artinya data produk tidak cukup untuk memverifikasi. "
    "Setiap temuan lapis-2 yang kamu kirim lewat `findings` harus mengutip draf "
    "persis; kutipan yang tidak ada di draf dibuang oleh server. "
    "run_cycle berhenti di LOLOS dan tidak pernah menerbitkan konten. "
    "Publikasi hanya lewat request_approval lalu approve_publication. "
    "approve_publication butuh kunci approval yang hanya dipegang manusia; "
    "nama approver diturunkan dari kuncinya, bukan dikirim sebagai argumen. "
    "Jangan pernah menyimpulkan bahwa konten sudah terbit."
)

mcp = MCPServer("lolos", instructions=INSTRUCTIONS, version="1.0.0")


# --------------------------------------------------------------------------- katalog
@mcp.tool()
def list_products() -> dict:
    """Daftar SKU yang dikenal: harga, promo, nomor BPOM, dan status halal.

    Panggil ini lebih dulu bila belum tahu SKU mana yang dimaksud.
    """
    return tools.list_products()


@mcp.tool()
def get_context(sku: str, platform: str) -> dict:
    """Muat lembar produk, brief, sertifikat, spesifikasi platform, dan batas keras.

    platform: tiktok | instagram | marketplace. Lembar produk adalah satu-satunya
    sumber fakta; brief tidak boleh menambah fakta baru.
    """
    return tools.get_context(sku, platform)


@mcp.tool()
def get_rulebook(rule_ids: list[str] | None = None) -> dict:
    """Baca aturan R-01..R-21 dan lapis mana yang memeriksa masing-masing.

    Tanpa argumen: seluruh rulebook. Dengan argumen: hanya aturan yang diminta.
    """
    return tools.get_rulebook(rule_ids)


# --------------------------------------------------------------------------- rencana & draf
@mcp.tool()
def plan_content(sku: str, platform: str, brief: str | None = None,
                 angle: str | None = None) -> dict:
    """Susun rencana tervalidasi dari lembar produk. Tidak menulis kalimat marketing.

    `brief` mengganti brief kampanye bawaan untuk satu panggilan ini saja.
    `angle` mengganti sudut cerita lalu memvalidasi ulang rencananya.
    """
    return tools.plan_content(sku, platform, brief, angle)


@mcp.tool()
def validate_plan(plan: dict) -> dict:
    """Validasi bentuk rencana sebelum dipakai. Menolak field wajib yang kosong."""
    return tools.validate_plan(plan)


@mcp.tool()
def write_draft(plan: dict, feedback: list[dict] | None = None,
                iteration: int = 1) -> dict:
    """Tulis draf dari rencana.

    `feedback` adalah daftar temuan Reviewer pada iterasi sebelumnya (field `temuan`
    dari review_draft). `iteration` dibatasi 1..3.
    """
    return tools.write_draft(plan, feedback, iteration)


@mcp.tool()
def review_draft(draft: str, sku: str, platform: str,
                 findings: list[dict] | None = None, iteration: int = 1,
                 write_audit: bool = False) -> dict:
    """Nilai draf dengan dua lapis dan kembalikan verdict beserta kutipan temuan.

    `findings` adalah temuan lapis-2 dari model pemanggil, berbentuk
    {"rule_id", "span", "reason", "fix"}. `span` harus mengutip draf persis;
    kutipan yang tidak ditemukan dibuang dan dilaporkan di `dibuang_llm`.

    Verdict: LOLOS (tidak ada pelanggaran), TOLAK (ada pelanggaran),
    PERLU_DATA (SKU tidak ada di registri — bukan lulus).
    """
    return tools.review_draft(draft, sku, platform, findings, iteration, write_audit)


@mcp.tool()
def run_cycle(sku: str, platform: str, brief: str | None = None) -> dict:
    """Jalankan Planner → Writer → Reviewer, maksimal tiga iterasi.

    Berhenti di LOLOS, PERLU_DATA, atau ESKALASI. Tidak pernah menerbitkan konten
    dan tidak pernah menyetujui apa pun.
    """
    return tools.run_cycle(sku, platform, brief)


# --------------------------------------------------------------------------- audit
@mcp.tool()
def audit_verify() -> dict:
    """Verifikasi rantai hash audit log. Mengembalikan utuh/rusak dan jumlah entri."""
    return tools.audit_verify()


@mcp.tool()
def audit_tail(n: int = 10) -> dict:
    """Ambil n entri audit terakhir. Maksimal 100."""
    return tools.audit_tail(n)


# --------------------------------------------------------------------------- approval
@mcp.tool()
def request_approval(sku: str, platform: str, content: str) -> dict:
    """Ajukan konten ke gerbang approval. Hasilnya PROPOSED, belum disetujui.

    Tampilkan `plan_id` kepada pengguna. Hanya manusia yang boleh melangkah ke
    approve_publication.
    """
    return tools.request_approval(sku, platform, content)


@mcp.tool()
def approve_publication(plan_id: str, approval_key: str, note: str = "") -> dict:
    """Setujui satu plan. Nama approver diturunkan dari kunci approval, bukan diklaim.

    Server menyimpan {"Nama": "<sha256(kunci)>"} per manusia di MCP_APPROVER_KEYS.
    Kunci yang cocok menentukan siapa yang menyetujui; pemohon tidak bisa
    menyetujui aksinya sendiri, dan agen tidak bisa menghasilkan kunci manusia.
    Tool ini tidak menerbitkan apa pun; status akhirnya APPROVED.
    """
    return tools.approve_publication(plan_id, approval_key, note)
