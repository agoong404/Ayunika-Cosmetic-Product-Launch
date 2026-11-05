"""
Cover image 16:9 untuk submission (checklist item 10).
Ukuran tampil 380x216; dirender 2x (760x432 @2x = 1520x864) supaya tajam.
Output: submission_templates/cover.png

Gaya mengikuti diagram arsitektur: latar putih, tinta #0f172a, aksen indigo #4338ca.
"""

W, H = 760, 432

INK = "#0f172a"
MUTED = "#64748b"
ACC = "#4338ca"
ACC_SOFT = "#e0e7ff"
AMBER = "#b45309"
GREEN = "#15803d"

out = []


def add(s):
    out.append(s)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, fill=INK, weight="400", anchor="start", ls=None):
    extra = f' letter-spacing="{ls}"' if ls else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}"{extra}>{esc(s)}</text>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Inter, system-ui, sans-serif">')
add('<defs>'
    '<filter id="sh" x="-30%" y="-30%" width="160%" height="180%">'
    '<feDropShadow dx="0" dy="1.5" stdDeviation="2.2" flood-color="#0f172a" flood-opacity="0.07"/>'
    '</filter></defs>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# ---------------------------------------------------------------- strip kiri
add('<rect x="0" y="0" width="10" height="432" fill="#4338ca"/>')

# ---------------------------------------------------------------- judul
text(52, 96, "LOLOS", 58, INK, "700", ls="2")
text(52, 130, "Reviewer konten peluncuran kosmetik: tolak, perbaiki, setujui.",
     16.5, MUTED, "400")

# ---------------------------------------------------------------- siklus mini
# tiga kotak kecil Planner -> Writer -> Reviewer dengan loop tolak
boxes = [("Planner", ACC, ACC_SOFT), ("Writer", "#1d4ed8", "#dbeafe"),
         ("Reviewer", AMBER, "#fef3c7")]
bx, by, bw, bh, gap = 52, 176, 132, 46, 56
centers = []
for i, (nama, a, t) in enumerate(boxes):
    x = bx + i * (bw + gap)
    add(f'<rect x="{x}" y="{by}" width="{bw}" height="{bh}" rx="10" fill="{t}" '
        f'stroke="{a}" stroke-width="1.3" filter="url(#sh)"/>')
    add(f'<circle cx="{x + 20}" cy="{by + bh / 2}" r="10" fill="{a}" opacity="0.9"/>')
    add(f'<text x="{x + 20}" y="{by + bh / 2 + 4}" font-size="11.5" fill="#ffffff" '
        f'font-weight="700" text-anchor="middle">{i + 1}</text>')
    add(f'<text x="{x + 38}" y="{by + bh / 2 + 4.5}" font-size="13" fill="{INK}" '
        f'font-weight="600">{nama}</text>')
    centers.append((x, x + bw))

# panah maju
for i in range(2):
    add(f'<line x1="{centers[i][1] + 4}" y1="{by + bh / 2}" x2="{centers[i + 1][0] - 4}" '
        f'y2="{by + bh / 2}" stroke="#94a3b8" stroke-width="1.8" '
        f'marker-end="url(#ar)"/>')
# panah tolak kembali (Reviewer -> Writer)
c1x = centers[1][0] + bw / 2
c2x = centers[2][0] + bw / 2
add(f'<path d="M {c2x} {by + bh} V {by + bh + 26} '
    f'H {c1x} V {by + bh + 4}" fill="none" stroke="#d97706" '
    f'stroke-width="1.8" stroke-dasharray="6 4" marker-end="url(#aa)"/>')
text((c1x + c2x) / 2, by + bh + 20,
     "TOLAK (R-xx) · maks 3 iterasi", 10.5, AMBER, "600", "middle")

add("""<defs>
  <marker id="ar" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#94a3b8"/></marker>
  <marker id="aa" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
    <path d="M0.5 0.5 L9.5 5 L0.5 9.5 z" fill="#d97706"/></marker>
</defs>""")

# ---------------------------------------------------------------- strip bukti
add('<rect x="52" y="286" width="656" height="66" rx="12" fill="#f8fafc" '
    'stroke="#e2e8f0" stroke-width="1.2"/>')
chips = [
    ("20 kasus × 50 ulangan", GREEN),
    ("21 aturan R-01..R-21", "#1d4ed8"),
    ("audit hash-chain", "#7c3aed"),
    ("approval manusia", ACC),
]
cx = 76
for label, col in chips:
    w = 20 + len(label) * 6.8
    add(f'<rect x="{cx}" y="302" width="{w:.0f}" height="34" rx="9" fill="#ffffff" '
        f'stroke="{col}" stroke-opacity="0.35" stroke-width="1.2"/>')
    add(f'<circle cx="{cx + 13}" cy="319" r="4.5" fill="{col}" opacity="0.85"/>')
    text(cx + 24, 323, label, 11, "#334155", "600")
    cx += w + 12

# ---------------------------------------------------------------- footer
text(52, 392, "Challenge C — The Creator Agent · Tencent Cloud Hackathon Indonesia 2026",
     11.5, MUTED, "400")
text(708, 392, "bodycare & beautycare", 11.5, ACC, "600", "end")

add("</svg>")

# ---------------------------------------------------------------- tulis + render
import subprocess
from pathlib import Path

svg = "\n".join(out)
here = Path(__file__).parent
(here / "cover.svg").write_text(svg, encoding="utf-8")

CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
wrapper = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    f"<style>html,body{{margin:0;padding:0;width:{W}px;height:{H}px;}}"
    f"svg{{display:block;width:{W}px;height:{H}px;}}</style></head>"
    f"<body>{svg}</body></html>"
)
html_path = here / "__render_cover.html"
html_path.write_text(wrapper, encoding="utf-8")
png_out = here.parent / "submission_templates" / "cover.png"
if CHROME.exists():
    subprocess.run([
        str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-sandbox", f"--screenshot={png_out.resolve()}",
        f"--window-size={W},{H}", "--force-device-scale-factor=2",
        html_path.resolve().as_uri(),
    ], check=True)
    print("wrote", png_out, png_out.stat().st_size, "bytes")
else:
    print("CHROME tidak ditemukan - render manual dari cover.svg")
html_path.unlink(missing_ok=True)
