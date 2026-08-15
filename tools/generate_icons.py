"""Generate window icon and tray PNG assets from SVG sources (requires Node resvg)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def main() -> None:
    script = TOOLS / "generate_icons.mjs"
    if not script.exists():
        raise SystemExit(f"Missing {script}")

    result = subprocess.run(
        ["npm", "install"],
        cwd=TOOLS,
        check=False,
        shell=True,
    )
    if result.returncode != 0:
        raise SystemExit("npm install failed in tools/")

    result = subprocess.run(
        ["node", str(script.name)],
        cwd=TOOLS,
        check=False,
        shell=True,
    )
    if result.returncode != 0:
        raise SystemExit("Icon generation failed")


if __name__ == "__main__":
    main()
