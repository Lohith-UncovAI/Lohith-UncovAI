#!/usr/bin/env python3
import sys
from pathlib import Path


def add_background(svg_path, fill):
    content = svg_path.read_text()
    if 'data-profile-bg="true"' in content:
        return

    opening_end = content.find(">")
    if opening_end == -1:
        raise ValueError(f"Invalid SVG: {svg_path}")

    background = (
        f'\n  <rect data-profile-bg="true" width="100%" height="100%" fill="#{fill}" />'
    )
    content = content[: opening_end + 1] + background + content[opening_end + 1 :]
    svg_path.write_text(content)


def main():
    if len(sys.argv) != 3:
        print("usage: add_snake_bg.py <dir> <hex-color>", file=sys.stderr)
        raise SystemExit(1)

    dist_dir = Path(sys.argv[1])
    fill = sys.argv[2].lstrip("#")

    for name in ("github-contribution-grid-snake.svg", "github-contribution-grid-snake-dark.svg"):
        add_background(dist_dir / name, fill)


if __name__ == "__main__":
    main()
