"""
sync.py — salin skill kanonik (folder ini) ke lokasi yang dibaca WorkBuddy.

Sumber kebenaran: skills/<nama>/ di repo.
Tujuan: .workbuddy-ai/skills/ (workspace) dan ~/.workbuddy-ai/skills/ (lintas proyek).

Pemakaian:
    python skills/sync.py                # keduanya
    python skills/sync.py --tujuan proyek
    python skills/sync.py --tujuan user
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMA = ("lolos-planner", "lolos-writer", "lolos-reviewer")


def tujuan(pilihan: str) -> list[Path]:
    proyek = HERE.parent / ".workbuddy-ai" / "skills"
    user = Path.home() / ".workbuddy-ai" / "skills"
    if pilihan == "proyek":
        return [proyek]
    if pilihan == "user":
        return [user]
    return [proyek, user]


def normalkan(dst: Path) -> int:
    """CRLF -> LF. Frontmatter yang berakhir \\r bisa gagal dikenali loader."""
    n = 0
    for f in dst.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".py"):
            b = f.read_bytes()
            if b"\r\n" in b:
                f.write_bytes(b.replace(b"\r\n", b"\n"))
                n += 1
    return n


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Sinkronkan skill Lolos ke lokasi WorkBuddy")
    ap.add_argument("--tujuan", choices=("semua", "proyek", "user"), default="semua")
    a = ap.parse_args(argv)

    gagal = 0
    for t in tujuan(a.tujuan):
        t.mkdir(parents=True, exist_ok=True)
        for n in NAMA:
            src = HERE / n
            if not (src / "SKILL.md").exists():
                print(f"  LEWATI {n}: sumber tidak lengkap")
                gagal += 1
                continue
            dst = t / n
            # dirs_exist_ok: menimpa isi tanpa menghapus folder
            shutil.copytree(src, dst, dirs_exist_ok=True)
            diubah = normalkan(dst)
            print(f"  {n:15s} -> {dst}"
                  + (f" (LF dinormalkan: {diubah})" if diubah else ""))

    print("\nSelesai. Mulai percakapan baru agar WorkBuddy memuat skill.")
    return 1 if gagal else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
