#!/usr/bin/env python3
"""Decorate Platane/snk snake SVGs with GitHub-native-style labels.

Adds to the raw snk grid SVG:
  - "<N> contributions in the last year" title (parsed from the public
    contribution calendar page, so it stays fresh on every scheduled run)
  - month labels above the grid (columns taken from the calendar's own
    colspan layout, guaranteed to align with snk's grid)
  - Mon / Wed / Fri weekday labels on the left
  - Less [c0..c4] More legend at the bottom right (colors reuse the CSS
    variables already defined inside the snk SVG, so light/dark stay in sync)

No third-party dependencies; runs in GitHub Actions and locally.
"""

import argparse
import os
import re
import sys
import urllib.request

GRID_X0 = 2      # x of first cell
GRID_Y0 = 2      # y of first cell
CELL = 12        # cell size
STEP = 16        # cell step
COLS = 53        # weeks in the calendar
GRID_RIGHT = GRID_X0 + (COLS - 1) * STEP + CELL   # 846

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

SRC_VIEWBOX = 'viewBox="-16 -32 880 192" width="880" height="192"'
DST_VIEWBOX = 'viewBox="-52 -92 920 252" width="920" height="252"'


def fetch_calendar(user: str) -> str:
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def parse_calendar(html: str):
    total = None
    m = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", html)
    if m:
        total = m.group(1)

    months = []
    col = 0
    pattern = (
        r'colspan="(\d+)"[^>]*>\s*<span class="sr-only">[^<]*</span>\s*'
        r'<span aria-hidden="true"[^>]*>([^<]+)</span>'
    )
    for span, name in re.findall(pattern, html):
        months.append((col, name.strip()))
        col += int(span)
    return total, months


def text(x, y, size, fill, body, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    return (f'<text x="{x}" y="{y}"{a} font-family="{FONT}" '
            f'font-size="{size}" fill="{fill}">{body}</text>')


def decorations(total, months, theme: str) -> str:
    fg = "#1f2328" if theme == "light" else "#f0f6fc"
    muted = "#59636e" if theme == "light" else "#9198a1"
    parts = []

    if total:
        parts.append(text(-14, -62, 18, fg, f"{total} contributions in the last year"))

    # month labels: 13px, baseline aligned with the title block above the grid
    for col, name in months:
        parts.append(text(GRID_X0 + col * STEP, -34, 13, muted, name))

    # weekday labels: 12px, right-aligned with a 10px gutter, vertically centered
    # on their grid row (baseline = row center + half cap height)
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        y = GRID_Y0 + row * STEP + CELL // 2 + 4
        parts.append(text(-10, y, 12, muted, label, anchor="end"))

    # legend: 11px text + 11px swatches, right edge flush with the grid
    ly = 130
    more_w, gap, sw, sw_step, less_w = 34, 6, 11, 14, 34
    x = GRID_RIGHT - (more_w + gap + 5 * sw_step - (sw_step - sw) + gap + less_w)
    parts.append(text(x, ly + sw - 1, 11, muted, "Less"))
    x += less_w + gap
    for i in range(5):
        parts.append(f'<rect x="{x}" y="{ly}" width="{sw}" height="{sw}" rx="2" fill="var(--c{i})"/>')
        x += sw_step
    parts.append(text(x + gap, ly + sw - 1, 11, muted, "More"))

    return "\n".join(parts)


def decorate(svg: str, deco: str) -> str:
    if SRC_VIEWBOX in svg:
        svg = svg.replace(SRC_VIEWBOX, DST_VIEWBOX, 1)
    else:
        # fall back to just widening whatever opening tag exists
        svg = re.sub(r'viewBox="[^"]*"', 'viewBox="-52 -92 920 252"', svg, count=1)
    assert "</svg>" in svg, "input does not look like an SVG"
    return svg.replace("</svg>", deco + "\n</svg>", 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER", "mxnklimt"))
    ap.add_argument("--light-in", default="dist/github-contribution-grid-snake.svg")
    ap.add_argument("--dark-in", default="dist/github-contribution-grid-snake-dark.svg")
    ap.add_argument("--light-out", default="dist/contribution-snake.svg")
    ap.add_argument("--dark-out", default="dist/contribution-snake-dark.svg")
    ap.add_argument("--html", default=None, help="use a local contributions HTML file instead of fetching")
    args = ap.parse_args()

    html = open(args.html, encoding="utf-8").read() if args.html else fetch_calendar(args.user)
    total, months = parse_calendar(html)
    print(f"total={total} months={len(months)}")

    for theme, src, dst in (("light", args.light_in, args.light_out),
                            ("dark", args.dark_in, args.dark_out)):
        svg = open(src, encoding="utf-8").read()
        out = decorate(svg, decorations(total, months, theme))
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        print(f"wrote {dst} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
