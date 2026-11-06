"""
build.py — hasilkan paket expert "Ayunika Compliance Team" dari sumber kanonik.

Sumber kebenaran:
  skills/<nama>/SKILL.md             → batas peran tiap anggota tim
  dataset_c/multilingual/facts.json  → kamus fakta tiga bahasa
  expert/ayunika-compliance-team/avatar-source.jpg → potret dasar

Yang dihasilkan (JANGAN diedit tangan):
  expert/ayunika-compliance-team/avatars/*.png

Pemakaian:
    python expert/build.py              # generate + validasi struktur
    python expert/build.py --pasang     # + salin ke my-experts + validate + register

Catatan desain:
- Paket ini TIDAK mendeklarasikan skills terpisah. Batas peran tiap anggota
  sudah tertulis di agent MD masing-masing, dan eksekusi lewat MCP. Menyalin
  SKILL.md lagi hanya menciptakan sumber kebenaran kelima yang bisa menyimpang.
- Skrip CLI dari skills/ juga tidak disalin: repo_root() berjalan mundur mencari
  engine/reviewer.py dan berakhir dengan SystemExit di dalam paket.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAKET = ROOT / "expert" / "ayunika-compliance-team"
SUMBER_AVATAR = PAKET / "avatar-source.jpg"

# Nama pendek, label peran, warna aksen, dan ikon tiap anggota.
ANGGOTA = [
    # id,                   nama,   peran,          aksen,    ikon
    ("ayunika-team-lead",  "Rani",  "TEAM LEAD",    "#D4AF37", "star"),
    ("ayunika-planner",    "Bima",  "CONTENT PLAN", "#2BB3A3", "clipboard"),
    ("ayunika-writer",     "Citra", "DRAFT WRITE",  "#4A90D9", "pencil"),
    ("ayunika-reviewer",   "Dimas", "CLAIM REVIEW", "#E05A5A", "shield"),
]


def rgb(hexa: str) -> tuple[int, int, int]:
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


def mix_hex(c1: tuple, c2: tuple, t: float) -> tuple[int, int, int]:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def gradient(w: int, h: int, top, bottom) -> "Image.Image":
    """Gradien vertikal; top/bottom boleh string hex atau tuple RGB."""
    from PIL import Image, ImageDraw
    tc = top if isinstance(top, tuple) else rgb(top)
    bc = bottom if isinstance(bottom, tuple) else rgb(bottom)
    img = Image.new("RGB", (w, h))
    for y in range(h):
        ImageDraw.Draw(img).line([(0, y), (w, y)], fill=mix_hex(tc, bc, y / (h - 1)))
    return img


def star_points(cx: float, cy: float, r: float, n: int = 5) -> list[tuple[float, float]]:
    import math
    pts = []
    for i in range(n * 2):
        ang = -math.pi / 2 + i * math.pi / n
        rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def draw_icon(d: "ImageDraw.ImageDraw", kind: str, cx: int, cy: int, col: tuple):
    """Gambar ikon putih di dalam lencana beraksen col."""
    w = 6
    if kind == "star":
        d.polygon(star_points(cx, cy, 20), fill=col)
    elif kind == "clipboard":
        d.rounded_rectangle((cx - 18, cy - 16, cx + 18, cy + 18), radius=5, outline=col, width=w)
        d.rectangle((cx - 8, cy - 24, cx + 8, cy - 12), fill=col)
        for yy in (-4, 4, 12):
            d.line((cx - 11, cy + yy, cx + 11, cy + yy), fill=col, width=3)
    elif kind == "pencil":
        d.line((cx - 16, cy + 14, cx + 12, cy - 14), fill=col, width=w)
        d.polygon([(cx + 12, cy - 14), (cx + 6, cy - 18), (cx + 16, cy - 8)], fill=col)
        d.line((cx - 18, cy + 16, cx - 12, cy + 10), fill=col, width=w)
    elif kind == "shield":
        d.polygon([(cx, cy - 18), (cx + 16, cy - 10), (cx + 16, cy + 6),
                   (cx, cy + 18), (cx - 16, cy + 6), (cx - 16, cy - 10)],
                  outline=col, width=w)
        d.line((cx - 7, cy + 1, cx - 1, cy + 8), fill=col, width=w, joint="curve")
        d.line((cx - 1, cy + 8, cx + 9, cy - 5), fill=col, width=w, joint="curve")


def make_member_avatar(base: "Image.Image", nama: str, peran: str,
                       aksen: str, ikon: str) -> "Image.Image":
    """Satu avatar 512×512: potret lingkar + gradien + lencana ikon + label."""
    from PIL import Image, ImageDraw, ImageFont

    S = 512
    ac = rgb(aksen)
    top_c = mix_hex(rgb("#0E2A47"), ac, 0.20)
    bg = gradient(S, S, top_c, "#06121F").convert("RGBA")

    # potret lingkar di tengah
    d_amt = 300
    cx, cy = 256, 232
    m = Image.new("L", (d_amt, d_amt), 0)
    ImageDraw.Draw(m).ellipse((0, 0, d_amt - 1, d_amt - 1), fill=255)
    por = Image.new("RGBA", (d_amt, d_amt))
    por.paste(base.resize((d_amt, d_amt), Image.LANCZOS), (0, 0))
    por.putalpha(m)
    bg.paste(por, (cx - d_amt // 2, cy - d_amt // 2), por)

    d = ImageDraw.Draw(bg, "RGBA")
    d.ellipse((cx - d_amt // 2, cy - d_amt // 2, cx + d_amt // 2, cy + d_amt // 2),
              outline=ac + (255,), width=7)

    # lencana ikon di atas
    bx, by, br = 256, 58, 34
    d.ellipse((bx - br, by - br, bx + br, by + br), fill=ac + (255,))
    draw_icon(d, ikon, bx, by, (255, 255, 255))

    # pita nama di bawah
    d.rectangle((0, 408, S, S), fill=(6, 16, 28, 230))
    d.rectangle((0, 408, S, 416), fill=ac + (255,))
    try:
        f_nama = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 46)
        f_peran = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    except OSError:
        f_nama = f_peran = ImageFont.load_default()
    d.text((256, 452), nama, font=f_nama, fill=(240, 246, 252, 255), anchor="mm")
    d.text((256, 488), peran, font=f_peran, fill=ac + (255,), anchor="mm")
    return bg.convert("RGB")


# ------------------------------------------------------------------ avatar
def generate_avatars() -> list[Path]:
    """Buat team.png + satu avatar per anggota dari potret sumber."""
    from PIL import Image, ImageDraw

    AV = PAKET / "avatars"
    AV.mkdir(parents=True, exist_ok=True)
    if not SUMBER_AVATAR.exists():
        raise SystemExit(f"Sumber avatar tidak ada: {SUMBER_AVATAR}")
    base = Image.open(SUMBER_AVATAR).convert("RGB")

    def simpan(img, nama):
        p = AV / nama
        img.save(p, "PNG", optimize=True)
        return p

    hasil = []
    buatan = []
    for aid, nama, peran, aksen, ikon in ANGGOTA:
        img = make_member_avatar(base, nama, peran, aksen, ikon)
        buatan.append(img)
        hasil.append(simpan(img, f"{aid}.png"))

    # Kartu tim: 2×2 dari keempat avatar anggota (beraksen beda).
    team = Image.new("RGB", (512, 512), "#06121F")
    for i, img in enumerate(buatan):
        team.paste(img.resize((256, 256), Image.LANCZOS), ((i % 2) * 256, (i // 2) * 256))
    ImageDraw.Draw(team).rectangle((0, 0, 511, 511), outline="#B5D4F4", width=4)
    hasil.append(simpan(team, "team.png"))
    return hasil


# ------------------------------------------------------------------ validasi
def validasi_struktur() -> list[str]:
    masalah = []
    pj = PAKET / ".codebuddy-plugin" / "plugin.json"
    data = json.loads(pj.read_text(encoding="utf-8"))

    if data.get("plugin") != data.get("name"):
        masalah.append("plugin != name")
    if data.get("expertType") != "team":
        masalah.append("expertType harus 'team'")
    if len(data.get("tags", [])) != 3:
        masalah.append("tags harus tepat 3")
    if len(data.get("quickPrompts", [])) != 3:
        masalah.append("quickPrompts harus tepat 3")
    if data["defaultInitPrompt"]["zh"] != data["quickPrompts"][0]["zh"]:
        masalah.append("defaultInitPrompt.zh != quickPrompts[0].zh")
    if not (PAKET / "settings.json").exists():
        masalah.append("settings.json wajib untuk team")

    for rel in data["agents"]:
        if not (PAKET / rel[2:]).exists():
            masalah.append(f"agent hilang: {rel}")
    members = data.get("members", [])
    if not members:
        masalah.append("members[] wajib untuk team")
    if not any(m.get("role") == "lead" for m in members):
        masalah.append("members[] harus punya satu role 'lead'")
    tim_info = data.get("teamInfo", {})
    if tim_info.get("leadAgent") in tim_info.get("memberAgents", []):
        masalah.append("memberAgents tidak boleh memuat lead")
    for m in members:
        if not (PAKET / m["avatar"]).exists():
            masalah.append(f"avatar anggota hilang: {m['avatar']}")
    if not (PAKET / data["avatar"]).exists():
        masalah.append("avatar tim hilang")

    for md in (PAKET / "agents").glob("*.md"):
        isi = md.read_text(encoding="utf-8")
        fm = isi.split("---")[1] if isi.startswith("---") else ""
        if "tools:" in fm:
            masalah.append(f"frontmatter memuat tools: {md.name}")
        if not re.search(r"^name:\s*" + re.escape(md.stem) + r"\s*$", fm, re.M):
            masalah.append(f"name frontmatter != nama file: {md.name}")
        for wajib in ("displayName", "profession"):
            if wajib not in fm:
                masalah.append(f"frontmatter tanpa {wajib}: {md.name}")

    setel = json.loads((PAKET / "settings.json").read_text(encoding="utf-8"))
    if setel.get("agent") != data.get("agentName"):
        masalah.append("settings.json agent != plugin.json agentName")

    if data.get("skills"):
        masalah.append("paket tim tidak boleh mendeklarasikan skills (batas peran ada di agent MD)")
    return masalah


def pasang() -> int:
    config = os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip() or str(Path.home() / ".workbuddy-ai")
    tujuan = Path(config) / "plugins" / "marketplaces" / "my-experts" / "plugins" / PAKET.name
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    if tujuan.exists():
        shutil.rmtree(tujuan)
    shutil.copytree(PAKET, tujuan, ignore=shutil.ignore_patterns("avatar-source.jpg"))
    print(f"Terpasang: {tujuan}")

    skrip = Path(r"C:/Users/Agung Wahyu Kusuma/AppData/Local/Programs/WorkBuddyAI/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/expert-manager/scripts")
    env = {**os.environ, "WORKBUDDY_CONFIG_DIR": str(config)}
    for nama in ("validate_expert.py", "register_expert.py"):
        r = subprocess.run([sys.executable, str(skrip / nama), str(tujuan)],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        print(f"\n--- {nama} ---\n{r.stdout.strip()}{r.stderr.strip()}")
        if r.returncode != 0:
            return r.returncode
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Bangun paket expert Ayunika Compliance Team")
    ap.add_argument("--pasang", action="store_true", help="salin ke my-experts lalu validasi & daftarkan")
    a = ap.parse_args()

    for p in generate_avatars():
        print(f"  generate {p.relative_to(PAKET)} ({p.stat().st_size // 1024} KB)")

    masalah = validasi_struktur()
    if masalah:
        print("\nGAGAL:")
        for m in masalah:
            print("  -", m)
        return 1
    print("\nStruktur paket valid.")

    if a.pasang:
        return pasang()
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
