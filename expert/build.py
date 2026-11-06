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

# Label dan warna aksen tiap anggota, untuk avatar.
ANGGOTA = [
    ("ayunika-team-lead", "R", "LEAD", "#D4AF37"),
    ("ayunika-planner", "B", "PLAN", "#5DCAA5"),
    ("ayunika-writer", "C", "WRITE", "#85B7EB"),
    ("ayunika-reviewer", "D", "REVIEW", "#F09595"),
]


def rgb(hexa: str) -> tuple[int, int, int]:
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


# ------------------------------------------------------------------ avatar
def generate_avatars() -> list[Path]:
    """Buat team.png + satu avatar per anggota dari potret sumber."""
    from PIL import Image, ImageDraw, ImageFont

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
    # Kartu tim: potret penuh dengan bingkai.
    team = Image.new("RGB", (512, 512), "#0C447C")
    kutip = base.resize((256, 256), Image.LANCZOS)
    for x, y in ((0, 0), (256, 0), (0, 256), (256, 256)):
        team.paste(kutip, (x, y))
    ImageDraw.Draw(team).rectangle((0, 0, 511, 511), outline="#B5D4F4", width=4)
    hasil.append(simpan(team, "team.png"))

    try:
        f_besar = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 54)
        f_kecil = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 34)
    except OSError:
        f_besar = f_kecil = ImageFont.load_default()

    for nama, huruf, label, aksen in ANGGOTA:
        im = base.resize((512, 512), Image.LANCZOS)
        dd = ImageDraw.Draw(im, "RGBA")
        dd.rectangle((0, 400, 512, 512), fill=(8, 26, 46, 225))
        dd.rectangle((0, 400, 512, 406), fill=rgb(aksen) + (255,))
        dd.ellipse((216, 316, 296, 396), fill=rgb(aksen) + (255,))
        dd.text((256, 356), huruf, font=f_besar, fill=(12, 32, 52, 255), anchor="mm")
        dd.text((256, 452), label, font=f_kecil, fill=(230, 240, 250, 255), anchor="mm")
        hasil.append(simpan(im, f"{nama}.png"))
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
