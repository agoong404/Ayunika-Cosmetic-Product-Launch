"""
Generator diagram arsitektur — Challenge C (Creator Agent).
Output: architecture_challenge_c.svg -> PNG 2x via Chrome headless.

Topologi berbeda dari Challenge A: bukan pipeline linear, tapi SIMPUL.
Inti visual = siklus Writer <-> Reviewer (tolak -> perbaiki -> setujui),
karena justru siklus itu yang dinilai juri.
"""

W, H = 1480, 1300

INK = "#0f172a"
MUTED = "#64748b"
FAINT = "#94a3b8"
LINE = "#e2e8f0"
SOFT = "#f8fafc"

ACC = {
    "input": ("#475569", "#f1f5f9"),
    "plan":  ("#4338ca", "#e0e7ff"),
    "write": ("#1d4ed8", "#dbeafe"),
    "review": ("#b45309", "#fef3c7"),
    "esc":   ("#b91c1c", "#fee2e2"),
    "appr":  ("#7c3aed", "#ede9fe"),
    "pub":   ("#0f766e", "#ccfbf1"),
    "audit": ("#15803d", "#dcfce7"),
}

# ---------------------------------------------------------------- geometry
BAND_Y, BAND_H = 176, 170
CARD_Y, CARD_H = 218, 110
IN_XS = [56, 330, 604, 878, 1152]
IN_W = 262

PLAN = (400, 386, 680, 90)        # x, y, w, h
WRIT = (240, 512, 440, 250)
REVI = (800, 512, 440, 250)
ESC = (280, 810, 400, 100)
APPR = (800, 810, 440, 100)
PUB = (800, 950, 440, 140)
CONTOH = (280, 950, 400, 140)
AUDIT_Y, AUDIT_H = 1140, 74

LOOP_L, LOOP_R = 680, 800         # celah antar kartu
LOOP_CX = 740


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


out = []


def add(s):
    out.append(s)


def text(x, y, s, size=12, fill=INK, weight="400", anchor="start",
         mono=False, ls=None, style=None, opacity=None):
    fam = ' font-family="Consolas, \'Cascadia Mono\', monospace"' if mono else ""
    extra = ""
    if ls:
        extra += f' letter-spacing="{ls}"'
    if style:
        extra += f' font-style="{style}"'
    if opacity:
        extra += f' opacity="{opacity}"'
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}"{fam}{extra}>{esc(s)}</text>')


def arrow(x1, y1, x2, y2, color="#94a3b8", mk="ar", w=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
        f'stroke-width="{w}"{d} marker-end="url(#{mk})" stroke-linecap="round"/>')


def poly(d, color, mk, w=1.8, dash="6 5"):
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" '
        f'stroke-dasharray="{dash}" marker-end="url(#{mk})" stroke-linejoin="round"/>')


def badge(x, y, n, accent, r=15):
    a, ab = ACC[accent]
    add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{ab}" stroke="{a}" stroke-width="1.3"/>')
    text(x, y + 4.4, n, 12.5, a, "700", "middle")


def cardbox(x, y, w, h, accent, tint="#ffffff", rx=12):
    a, _ = ACC[accent]
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{tint}" '
        f'stroke="{LINE}" stroke-width="1.4" filter="url(#sh)"/>')
    add(f'<rect x="{x + 1}" y="{y + 18}" width="4" height="{h - 36}" rx="2" '
        f'fill="{a}" opacity="0.9"/>')


# ---------------------------------------------------------------- document
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Inter, system-ui, sans-serif">')
add("""<defs>
  <filter id="sh" x="-30%" y="-30%" width="160%" height="180%">
    <feDropShadow dx="0" dy="1.5" stdDeviation="2.2" flood-color="#0f172a" flood-opacity="0.06"/>
  </filter>
  <marker id="ar" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#94a3b8"/></marker>
  <marker id="arb" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#1d4ed8"/></marker>
  <marker id="ara" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#d97706"/></marker>
  <marker id="arr" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#dc2626"/></marker>
  <marker id="arv" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#7c3aed"/></marker>
  <marker id="arg" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#15803d"/></marker>
</defs>""")
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# ---------------------------------------------------------------- header
text(40, 58, "Arsitektur Agent — Creator Agent", 27, INK, "700")
text(40, 84, "Challenge C · tim 3 agent: Planner · Writer · Reviewer · siklus tolak → "
             "perbaiki → setujui", 13, MUTED)

# ---------------------------------------------------------------- legend
add(f'<rect x="40" y="106" width="1400" height="46" rx="10" fill="{SOFT}" stroke="{LINE}" stroke-width="1"/>')
ly = 129
lx = 64


def legend(x, color, dash, label, mk):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x}" y1="{ly}" x2="{x + 26}" y2="{ly}" stroke="{color}" '
        f'stroke-width="2"{d} marker-end="url(#{mk})"/>')
    text(x + 36, ly + 4, label, 11.5, "#475569")
    return x + 36 + len(label) * 6.4 + 26


lx = legend(lx, "#94a3b8", None, "alur kerja", "ar")
lx = legend(lx, "#d97706", "6 4", "tolakan + revisi (loop)", "ara")
lx = legend(lx, "#dc2626", "6 4", "eskalasi ke manusia", "arr")
lx = legend(lx, "#1d4ed8", "5 4", "aturan mengikat", "arb")
add(f'<circle cx="{lx + 4}" cy="{ly}" r="5" fill="#15803d" opacity="0.55"/>')
text(lx + 16, ly + 4, "log & riwayat revisi", 11.5, "#475569")

# ---------------------------------------------------------------- input band
add(f'<rect x="40" y="{BAND_Y}" width="1400" height="{BAND_H}" rx="14" fill="#fcfdff" '
    f'stroke="{LINE}" stroke-width="1.4"/>')
text(60, BAND_Y + 28, "SUMBER FAKTA & ATURAN", 11.5, FAINT, "700", ls="1.4")
text(1420, BAND_Y + 28, "Writer hanya boleh memakai fakta dari sini", 11, MUTED, "400", "end")

INPUTS = [
    ("BRF-001", "Brief", "Sasaran, platform, pesan kunci"),
    ("PS-001..004", "Lembar produk", "Harga, isi, kuota, nomor sertifikat"),
    ("R-01..R-21", "Rulebook", "Dasar penolakan, per nomor aturan"),
    ("tone guide", "Nada merek", "Hangat, jujur, santai-profesional"),
    ("3 platform", "Spesifikasi platform", "Durasi, karakter, struktur"),
]
for i, (kode, judul, isi) in enumerate(INPUTS):
    x = IN_XS[i]
    add(f'<rect x="{x}" y="{CARD_Y}" width="{IN_W}" height="{CARD_H}" rx="10" fill="#ffffff" '
        f'stroke="{LINE}" stroke-width="1.2"/>')
    text(x + 16, CARD_Y + 24, kode, 10.5, FAINT, "600", mono=True)
    text(x + 16, CARD_Y + 46, judul, 13, INK, "600")
    text(x + 16, CARD_Y + 70, isi, 10.8, MUTED)

arrow(LOOP_CX, BAND_Y + BAND_H, LOOP_CX, PLAN[1] - 1)

# rulebook mengikat Reviewer secara langsung
poly(f"M {IN_XS[2] + IN_W} {CARD_Y + CARD_H} V {BAND_Y + BAND_H + 8} H 1150 V {REVI[1] - 2}",
     "#1d4ed8", "arb", 1.6, "5 4")
text(1158, 430, "R-xx", 10, "#1d4ed8", "600")

# ---------------------------------------------------------------- planner
px, py, pw, ph = PLAN
cardbox(px, py, pw, ph, "plan")
badge(px + 40, py + ph / 2, "1", "plan")
text(px + 68, py + 34, "Planner", 14.6, INK, "600")
text(px + 68, py + 55, "Brief → rencana per platform: sudut, struktur, fakta mana yang dipakai",
     11.8, MUTED)
text(px + 68, py + 73, "Tidak menulis kalimat — hanya kerangka yang bisa diperiksa",
     11.8, MUTED)

arrow(LOOP_CX, py + ph, LOOP_CX, WRIT[1] - 1)

# ---------------------------------------------------------------- writer
wx, wy, ww, wh = WRIT
cardbox(wx, wy, ww, wh, "write", "#fbfcff")
badge(wx + 40, wy + 44, "2", "write")
text(wx + 68, wy + 38, "Writer", 14.6, INK, "600")
text(wx + 68, wy + 59, "Menulis draf dari kerangka + fakta lembar produk", 11.8, MUTED)
text(wx + 68, wy + 77, "Memperbaiki draf yang ditolak Reviewer", 11.8, MUTED)
text(wx + 68, wy + 95, "Tidak menambah fakta di luar lembar produk", 11.8, MUTED)

# strip versi draf
add(f'<rect x="{wx + 24}" y="{wy + 150}" width="{ww - 48}" height="72" rx="9" '
    f'fill="#ffffff" stroke="{LINE}" stroke-width="1.2"/>')
text(wx + 40, wy + 172, "VERSI DRAF", 10, FAINT, "700", ls="1.2")
for i, (v, st) in enumerate([("v1", "ditolak"), ("v2", "ditolak"), ("v3", "lolos")]):
    cxx = wx + 46 + i * 122
    col = "#15803d" if st == "lolos" else "#b45309"
    add(f'<circle cx="{cxx + 5}" cy="{wy + 192}" r="5" fill="{col}" opacity="0.7"/>')
    text(cxx + 18, wy + 196, v, 11.5, INK, "600", mono=True)
    text(cxx + 42, wy + 196, st, 10.8, MUTED)

# ---------------------------------------------------------------- reviewer
rx, ry, rw, rh = REVI
cardbox(rx, ry, rw, rh, "review", "#fffdf7")
badge(rx + 40, ry + 44, "3", "review")
text(rx + 68, ry + 38, "Reviewer", 14.6, INK, "600")
text(rx + 68, ry + 59, "Menilai setiap draf terhadap R-01..R-21 + batas platform", 11.8, MUTED)

# lapis deterministik
add(f'<rect x="{rx + 24}" y="{ry + 74}" width="{rw - 48}" height="72" rx="9" '
    f'fill="#ffffff" stroke="#fde68a" stroke-width="1.2"/>')
text(rx + 40, ry + 94, "DETERMINISTIK — kode", 9.8, "#b45309", "700", ls="1.1")
text(rx + 40, ry + 114, "R-03 klaim halal vs registri · R-06 harga/angka/kuota", 10.9, "#475569")
text(rx + 40, ry + 132, "frasa terlarang · disclaimer · emoji · batas platform", 10.9, "#475569")

# lapis LLM
add(f'<rect x="{rx + 24}" y="{ry + 156}" width="{rw - 48}" height="66" rx="9" '
    f'fill="#ffffff" stroke="#e0e7ff" stroke-width="1.2"/>')
text(rx + 40, ry + 176, "LAPIS MODEL — wajib kutip teks draf", 9.8, "#4338ca", "700", ls="1.1")
text(rx + 40, ry + 196, "R-04 klaim tak terverifikasi · R-07 superlatif", 10.9, "#475569")
text(rx + 40, ry + 213, "R-05 testimoni · R-10 nada · R-12 kompetitor", 10.9, "#475569")

# ---------------------------------------------------------------- loop arrows
arrow(LOOP_L, 590, LOOP_R - 2, 590, "#1d4ed8", "arb", 2)
text(LOOP_CX, 580, "draf baru", 10.2, "#1d4ed8", "600", "middle")

arrow(LOOP_R, 700, LOOP_L + 2, 700, "#d97706", "ara", 2, "6 4")
text(LOOP_CX, 722, "TOLAK (R-xx)", 10.2, "#b45309", "600", "middle")

add(f'<rect x="{LOOP_CX - 44}" y="632" width="88" height="24" rx="12" fill="#fffbeb" '
    f'stroke="#fde68a" stroke-width="1"/>')
text(LOOP_CX, 648, "iterasi 1 / 3", 10, "#b45309", "700", "middle")

# ---------------------------------------------------------------- eskalasi
ex, ey, ew, eh = ESC
cardbox(ex, ey, ew, eh, "esc", "#fffbfb")
badge(ex + 40, ey + eh / 2, "!", "esc")
text(ex + 68, ey + 40, "Eskalasi ke manusia", 13.6, INK, "600")
text(ex + 68, ey + 60, "Iterasi mencapai 3 → berhenti, bukan berputar", 11.2, MUTED)
text(ex + 68, ey + 77, "Serahkan sisa masalah + riwayat ke manusia", 11.2, MUTED)

poly(f"M 860 {REVI[1] + rh} V 786 H 600 V {ey - 2}", "#dc2626", "arr", 1.8, "6 5")
text(748, 779, "iterasi habis", 10, "#dc2626", "600", "middle")

# ---------------------------------------------------------------- approval
ax, ay, aw, ah = APPR
cardbox(ax, ay, aw, ah, "appr", "#fcfaff")
badge(ax + 40, ay + ah / 2, "✓", "appr")
text(ax + 68, ay + 40, "Persetujuan manusia", 13.6, INK, "600")
text(ax + 68, ay + 60, "Marketing Lead menyetujui konten final", 11.2, MUTED)
text(ax + 68, ay + 77, "Tidak ada yang terbit sebelum langkah ini", 11.2, MUTED)

arrow(1020, REVI[1] + rh, 1020, ay - 1, "#7c3aed", "arv", 2)
text(1028, 792, "LOLOS", 10.2, "#6d28d9", "600")

# ---------------------------------------------------------------- publish
ux, uy, uw, uh = PUB
cardbox(ux, uy, uw, uh, "pub", "#f7fefd")
text(ux + 24, uy + 30, "PUBLIKASI — minimal 2 platform", 10, FAINT, "700", ls="1.2")
chips = ["Naskah TikTok", "Caption Instagram", "Listing marketplace"]
for i, c in enumerate(chips):
    cw = 126
    cx = ux + 24 + i * (cw + 8)
    add(f'<rect x="{cx}" y="{uy + 48}" width="{cw}" height="34" rx="8" fill="#ffffff" '
        f'stroke="#99f6e4" stroke-width="1.2"/>')
    text(cx + cw / 2, uy + 70, c, 10.6, "#0f766e", "600", "middle")
text(ux + 24, uy + 108, "Hanya setelah disetujui; setiap klaim tertaut ke lembar produk",
     10.6, MUTED)
text(ux + 24, uy + 126, "Fakta, harga, dan nomor sertifikat tidak boleh menyimpang", 10.6, MUTED)

arrow(1020, uy + uh, 1020, AUDIT_Y - 1, "#15803d", "arg", 1.8, "4 4")

# ---------------------------------------------------------------- contoh siklus
sx, sy, sw, sh = CONTOH
add(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="12" fill="#fcfdff" '
    f'stroke="{LINE}" stroke-width="1.4"/>')
text(sx + 20, sy + 26, "CONTOH SIKLUS (yang dinilai juri)", 10, FAINT, "700", ls="1.2")
SIKLUS = [
    ("v1", "ditolak", "R-03+R-06 kode · R-04+R-10 model", "#b45309"),
    ("v2", "ditolak", "R-14 'semua jenis kulit' (kode)", "#b45309"),
    ("v3", "lolos", "lapis-1 & lapis-2 0 temuan → disetujui", "#15803d"),
]
for i, (v, st, why, col) in enumerate(SIKLUS):
    yy = sy + 52 + i * 28
    add(f'<circle cx="{sx + 26}" cy="{yy - 4}" r="5" fill="{col}" opacity="0.7"/>')
    text(sx + 40, yy, v, 11, INK, "600", mono=True)
    text(sx + 62, yy, why, 10.4, MUTED)

arrow(sx + sw / 2, sy + sh, sx + sw / 2, AUDIT_Y - 1, "#15803d", "arg", 1.8, "4 4")

# ---------------------------------------------------------------- audit rail
add(f'<rect x="40" y="{AUDIT_Y}" width="1400" height="{AUDIT_H}" rx="12" fill="#f2fdf6" '
    f'stroke="#bbf7d0" stroke-width="1.4"/>')
add(f'<circle cx="70" cy="{AUDIT_Y + 26}" r="6" fill="#15803d" opacity="0.75"/>')
text(88, AUDIT_Y + 31, "RIWAYAT REVISI & LOG", 13, "#15803d", "700")
text(88, AUDIT_Y + 50, "append-only · hash chain · tidak bisa diubah agent", 10.6, "#4d7c0f")
text(1420, AUDIT_Y + 31, "Planner → Writer → Reviewer → tolakan → revisi → persetujuan",
     12, "#166534", "600", "end")
text(1420, AUDIT_Y + 50, "setiap pertukaran antar-agent dan alasan tolakan tersimpan",
     10.6, "#4d7c0f", "400", "end")

# ---------------------------------------------------------------- footer
text(40, 1262, "Reviewer dua lapis: kode vs pola (R-03/R-06/R-07), model vs nada & parafrase "
               "(R-04/R-05/R-10/R-12). Setiap temuan wajib mengutip teks yang ADA di draf.",
     10.5, FAINT)

add("</svg>")

with open("architecture_challenge_c.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote architecture_challenge_c.svg")

# ---- render PNG 2x via Chrome headless (cara sama seperti engine/buat_bukti.py) ----
import subprocess
from pathlib import Path

CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
svg = "\n".join(out)
wrapper = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    f"<style>html,body{{margin:0;padding:0;width:{W}px;height:{H}px;}}"
    f"svg{{display:block;width:{W}px;height:{H}px;}}</style></head>"
    f"<body>{svg}</body></html>"
)
html_path = Path("__render_arch.html")
html_path.write_text(wrapper, encoding="utf-8")
png_path = Path("architecture_challenge_c.png")
if CHROME.exists():
    subprocess.run([
        str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-sandbox", f"--screenshot={png_path.resolve()}",
        f"--window-size={W},{H}", "--force-device-scale-factor=2",
        html_path.resolve().as_uri(),
    ], check=True)
    print("wrote", png_path, png_path.stat().st_size, "bytes")
else:
    print("CHROME tidak ditemukan di", CHROME, "- PNG tidak dibuat; render manual dari SVG")
html_path.unlink(missing_ok=True)
