#!/usr/bin/env python3
"""Fetch vn7n24fzkq/github-profile-summary-cards card SVGs and strip their
built-in titles ("Stats", "Top Languages by Commit", ...).

The summary-cards API offers no "hide title" option, so we post-process:
  1. remove the title <text ... font-size: 22px ...> element
  2. shift the body group (translate(0,40)) up to translate(0,10)
  3. shrink the viewport from 340x200 to 340x170

Result: a clean borderless transparent card that blends into the README.
Runs in GitHub Actions and locally (use --stats-file/--langs-file to skip
fetching when testing). No third-party dependencies.
"""

import argparse
import os
import re
import sys
import urllib.request

CARDS = {
    "stats": "https://github-profile-summary-cards.vercel.app/api/cards/stats?username={user}&theme=transparent",
    "langs": "https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username={user}&theme=transparent",
}

SRC_HEADER = 'width="340" height="200" viewBox="0 0 340 200"'
DST_HEADER = 'width="340" height="170" viewBox="0 0 340 170"'

# the title is the only 22px text in the card
TITLE_RE = re.compile(r'<text x="30" y="40" class="gpsc-item"[^>]*font-size: 22px;[^>]*>[^<]*</text>')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def strip_title(svg: str) -> str:
    out, n = TITLE_RE.subn("", svg, count=1)
    assert n == 1, "title text not found - card layout may have changed"
    assert 'transform="translate(0,40)"' in out, "body group not found"
    out = out.replace('transform="translate(0,40)"', 'transform="translate(0,10)"', 1)
    assert SRC_HEADER in out, "unexpected svg header"
    out = out.replace(SRC_HEADER, DST_HEADER, 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER", "mxnklimt"))
    ap.add_argument("--stats-file", default=None, help="local stats SVG instead of fetching")
    ap.add_argument("--langs-file", default=None, help="local most-commit-language SVG instead of fetching")
    ap.add_argument("--stats-out", default="dist/stats-card.svg")
    ap.add_argument("--langs-out", default="dist/langs-card.svg")
    args = ap.parse_args()

    for kind, url_tpl, src, dst in (
        ("stats", CARDS["stats"], args.stats_file, args.stats_out),
        ("langs", CARDS["langs"], args.langs_file, args.langs_out),
    ):
        svg = open(src, encoding="utf-8").read() if src else fetch(url_tpl.format(user=args.user))
        out = strip_title(svg)
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        print(f"wrote {dst} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
