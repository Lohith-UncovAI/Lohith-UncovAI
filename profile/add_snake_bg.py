#!/usr/bin/env python3
import re
import sys
from pathlib import Path


THEMED_VIEWBOX = "-16 -40 880 224"
THEMED_WIDTH = "880"
THEMED_HEIGHT = "224"


def themed_shell(fill):
    return f"""
  <defs>
    <linearGradient id="snake-stage" x1="0" y1="-40" x2="0" y2="184" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0a0e16" />
      <stop offset="60%" stop-color="#05070d" />
      <stop offset="100%" stop-color="#020306" />
    </linearGradient>
    <linearGradient id="snake-panel" x1="0" y1="-24" x2="848" y2="160" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0b1018" />
      <stop offset="55%" stop-color="#060a11" />
      <stop offset="100%" stop-color="#03050a" />
    </linearGradient>
    <linearGradient id="snake-sheen" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0" />
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.09" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="snake-beam" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#f5d25f" stop-opacity="0.48" />
      <stop offset="40%" stop-color="#f5d25f" stop-opacity="0.16" />
      <stop offset="100%" stop-color="#f4d35e" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="snake-floor" x1="0" y1="144" x2="0" y2="184" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#05070d" stop-opacity="0" />
      <stop offset="100%" stop-color="#020306" stop-opacity="1" />
    </linearGradient>
    <radialGradient id="snake-moon" cx="50%" cy="50%" r="60%">
      <stop offset="0%" stop-color="#fff8cf" />
      <stop offset="72%" stop-color="#f5d25f" stop-opacity="0.95" />
      <stop offset="100%" stop-color="#f4d35e" stop-opacity="0.08" />
    </radialGradient>
    <radialGradient id="snake-ember" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f5d25f" stop-opacity="0.95" />
      <stop offset="100%" stop-color="#f5d25f" stop-opacity="0" />
    </radialGradient>
    <pattern id="snake-grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M20 0H0V20" fill="none" stroke="#111827" stroke-width="1" opacity="0.22" />
    </pattern>
    <filter id="snake-blur" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="10" />
    </filter>
    <clipPath id="snake-panel-clip">
      <rect x="-12" y="-36" width="872" height="216" rx="22" />
    </clipPath>
    <style>
      .snake-ui {{
        font-family: "Ubuntu Mono", "SFMono-Regular", "Consolas", monospace;
        letter-spacing: 0.5px;
      }}
    </style>
  </defs>
  <g data-profile-bg="true" clip-path="url(#snake-panel-clip)">
    <rect x="-16" y="-40" width="880" height="224" rx="24" fill="#{fill}" />
    <rect x="-16" y="-40" width="880" height="224" rx="24" fill="url(#snake-stage)" />
    <rect x="-12" y="-36" width="872" height="216" rx="22" fill="none" stroke="#1b2433" stroke-width="1.4" />
    <rect x="-2" y="-24" width="852" height="184" rx="18" fill="url(#snake-panel)" stroke="#161d29" />
    <rect x="-2" y="-24" width="852" height="184" rx="18" fill="url(#snake-grid)" opacity="0.26" />
    <path d="M-2 124 H850 V160 H-2 Z" fill="url(#snake-floor)" />
    <rect x="-2" y="-24" width="852" height="1" fill="#1f2838" opacity="0.85" />
    <rect x="-110" y="-24" width="112" height="184" fill="url(#snake-sheen)" opacity="0.20">
      <animate attributeName="x" values="-110;910;-110" dur="8.4s" repeatCount="indefinite" />
    </rect>

    <g transform="translate(18 -27)">
      <circle cx="0" cy="0" r="4.5" fill="#f5d25f" />
      <circle cx="16" cy="0" r="4.5" fill="#f5d25f" />
      <circle cx="32" cy="0" r="4.5" fill="#f5d25f" />
      <circle cx="48" cy="0" r="4.5" fill="#f5d25f" opacity="0.78" />
      <text x="70" y="4" class="snake-ui" fill="#f5d25f" font-size="12">gotham.signal</text>
      <text x="236" y="4" class="snake-ui" fill="#74839f" font-size="10">contribution patrol // lohith</text>
    </g>

    <g transform="translate(748 -18)">
      <circle cx="0" cy="0" r="18" fill="#f5d25f" opacity="0.10" filter="url(#snake-blur)" />
      <circle cx="0" cy="0" r="13" fill="url(#snake-moon)" />
      <g opacity="0.9">
        <path d="M0,-4 C-6,-10 -12,-8 -18,-1 C-23,-1 -31,-5 -37,-14 C-39,-6 -35,0 -28,5 C-21,11 -14,11 -7,8 C-5,12 -3,16 0,20 C3,16 5,12 7,8 C14,11 21,11 28,5 C35,0 39,-6 37,-14 C31,-5 23,-1 18,-1 C12,-8 6,-10 0,-4 Z" fill="#0a0d14">
          <animateTransform attributeName="transform" type="translate" values="0 0;12 -4;24 0" dur="8.6s" repeatCount="indefinite" />
        </path>
      </g>
    </g>

    <g transform="translate(660 142)" opacity="0.78">
      <circle cx="0" cy="0" r="5" fill="#f5d25f" />
      <circle cx="0" cy="0" r="12" fill="none" stroke="#f5d25f" stroke-opacity="0.32">
        <animate attributeName="r" values="8;20;8" dur="2.9s" repeatCount="indefinite" />
        <animate attributeName="stroke-opacity" values="0.28;0;0.28" dur="2.9s" repeatCount="indefinite" />
      </circle>
      <g>
        <animateTransform attributeName="transform" type="rotate" values="-9 0 0;10 0 0;-9 0 0" dur="7.4s" repeatCount="indefinite" />
        <polygon points="0,0 112,-112 194,-74 38,10" fill="url(#snake-beam)" />
      </g>
    </g>

    <g opacity="0.92">
      <path d="M-2 160 L-2 124 L28 124 L28 92 L54 92 L54 132 L86 132 L86 102 L110 102 L110 160 Z" fill="#0a1019" />
      <path d="M74 160 L74 104 L108 104 L108 74 L136 74 L136 160 Z" fill="#0e1521" />
      <path d="M128 160 L128 86 L162 86 L162 108 L190 108 L190 66 L220 66 L220 160 Z" fill="#0b111b" />
      <path d="M198 160 L198 116 L230 116 L230 88 L260 88 L260 160 Z" fill="#070b12" />
      <path d="M250 160 L250 78 L288 78 L288 42 L318 42 L318 160 Z" fill="#0e1521" />
      <path d="M718 160 L718 110 L748 110 L748 66 L780 66 L780 160 Z" fill="#0a1019" />
      <path d="M772 160 L772 84 L808 84 L808 44 L840 44 L840 160 Z" fill="#0e1521" />
      <path d="M828 160 L828 116 L850 116 L850 160 Z" fill="#070b12" />
    </g>

    <g opacity="0.75">
      <rect x="20" y="134" width="4" height="6" fill="#f5d25f" />
      <rect x="54" y="118" width="4" height="6" fill="#f5d25f" />
      <rect x="98" y="130" width="4" height="6" fill="#f5d25f" />
      <rect x="154" y="102" width="4" height="6" fill="#f5d25f" />
      <rect x="208" y="94" width="4" height="6" fill="#f5d25f" />
      <rect x="740" y="126" width="4" height="6" fill="#f5d25f" />
      <rect x="786" y="96" width="4" height="6" fill="#f5d25f" />
      <rect x="824" y="136" width="4" height="6" fill="#f5d25f" />
    </g>

    <g opacity="0.48">
      <circle cx="286" cy="18" r="8" fill="url(#snake-ember)">
        <animate attributeName="cy" values="18;116;18" dur="8.8s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0.42;0" dur="8.8s" repeatCount="indefinite" />
      </circle>
      <circle cx="512" cy="6" r="6" fill="url(#snake-ember)">
        <animate attributeName="cy" values="6;124;6" dur="7.1s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0.32;0" dur="7.1s" repeatCount="indefinite" />
      </circle>
      <circle cx="602" cy="10" r="5" fill="url(#snake-ember)">
        <animate attributeName="cy" values="10;108;10" dur="6.4s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0.28;0" dur="6.4s" repeatCount="indefinite" />
      </circle>
    </g>
  </g>
"""


def retheme_root(content):
    content = re.sub(r'viewBox="[^"]+"', f'viewBox="{THEMED_VIEWBOX}"', content, count=1)
    content = re.sub(r'width="[^"]+"', f'width="{THEMED_WIDTH}"', content, count=1)
    content = re.sub(r'height="[^"]+"', f'height="{THEMED_HEIGHT}"', content, count=1)
    return content


def theme_snake(svg_path, fill):
    content = svg_path.read_text()
    if 'data-profile-bg="true"' in content:
        return

    content = retheme_root(content)
    opening_match = re.search(r"<svg[^>]*>", content)
    if not opening_match:
        raise ValueError(f"Invalid SVG: {svg_path}")

    insert_at = opening_match.end()
    content = content[:insert_at] + themed_shell(fill) + content[insert_at:]
    svg_path.write_text(content)


def main():
    if len(sys.argv) != 3:
        print("usage: add_snake_bg.py <dir> <hex-color>", file=sys.stderr)
        raise SystemExit(1)

    dist_dir = Path(sys.argv[1])
    fill = sys.argv[2].lstrip("#")

    for name in ("github-contribution-grid-snake.svg", "github-contribution-grid-snake-dark.svg"):
        theme_snake(dist_dir / name, fill)


if __name__ == "__main__":
    main()
