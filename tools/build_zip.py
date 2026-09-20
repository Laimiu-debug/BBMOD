#!/usr/bin/env python3
"""Build mod_afei_expedition.zip for Battle Brothers data/ and BBMOD inspect_archive."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = DIST / "mod_afei_expedition.zip"
INCLUDE_ROOTS = ("scripts", "gfx")
ROOT_SIDE_FILES = ("README.md", "LICENSE.txt", "BBMOD_ATTRIBUTION.txt", "STAGE1.md")
SCRIPT_SUFFIXES = {".nut", ".cnut", ".txt", ".md", ".json"}
GFX_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root_name in INCLUDE_ROOTS:
            base = ROOT / root_name
            if not base.exists():
                # gfx optional only if absent; scripts required
                if root_name == "scripts":
                    print(f"missing {base}", file=sys.stderr)
                    return 1
                continue
            allowed = SCRIPT_SUFFIXES if root_name == "scripts" else GFX_SUFFIXES | SCRIPT_SUFFIXES
            for path in sorted(base.rglob("*")):
                if path.is_file() and path.suffix.lower() in allowed:
                    arc = path.relative_to(ROOT).as_posix()
                    zf.write(path, arcname=arc)
        for name in ROOT_SIDE_FILES:
            path = ROOT / name
            if path.exists():
                zf.write(path, arcname=name)

    # Prefer BBMOD inspect_archive when available (this Cloud Agent workspace).
    bbmod_safety = Path("/workspace/app/core/archive_safety.py")
    if bbmod_safety.exists():
        sys.path.insert(0, str(Path("/workspace/app")))
        from core.archive_safety import inspect_archive  # type: ignore

        with OUT.open("rb") as fh:
            info = inspect_archive(fh)
        print("inspect_archive OK:", info)
    else:
        # Minimal structural check matching BBMOD roots policy.
        with zipfile.ZipFile(OUT) as zf:
            names = zf.namelist()
        if not any(n.startswith("scripts/") for n in names):
            print("ZIP missing scripts/", file=sys.stderr)
            return 1
        print("built", OUT, "entries", len(names), "(BBMOD inspect_archive not found; structural check only)")

    print("output:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
