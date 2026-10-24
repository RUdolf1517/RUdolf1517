#!/usr/bin/env python3
"""Render the language-split card for the profile README.

Aggregates bytes of code per language across all public, non-fork repositories
and writes two theme-matched SVGs:

    assets/langs-dark.svg
    assets/langs-light.svg

Replaces the third-party github-readme-stats card, so the profile has no external
image dependency that can rate-limit or go down. Standard library only:

    GITHUB_TOKEN=... python3 scripts/gen_langs.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from theme import MONO, SANS, THEMES

LOGIN = os.environ.get("PROFILE_LOGIN", "RUdolf1517")
API = "https://api.github.com/graphql"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

W, H = 1000, 230
TOP_N = 6

# A curated palette instead of the saturated GitHub language colours: these sit
# next to the amber/blue accents of the banner without fighting them.
PALETTE = {
    "Python": "#4F8DF7",
    "Rust": "#F0A87B",
    "JavaScript": "#E4C76C",
    "TypeScript": "#7FB2FF",
    "HTML": "#C97B5A",
    "CSS": "#8B7BD8",
    "Shell": "#6EE7B7",
    "PowerShell": "#6C8EBF",
    "Ruby": "#D4707A",
    "C": "#8FA3BF",
    "C++": "#9C8AD6",
    "Other": "#5C6B7F",
}

QUERY = """
query($login:String!, $cursor:String) {
  user(login:$login) {
    repositories(first:100, after:$cursor, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        languages(first:12, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def gql(query: str, variables: dict, token: str) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-langs-card",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:  # pragma: no cover - network only
        sys.exit(f"GitHub API error {exc.code}: {exc.read().decode()[:400]}")
    if "errors" in payload:
        sys.exit(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


def collect(token: str) -> dict:
    totals: dict[str, dict] = {}
    cursor = None
    repos = 0
    while True:
        data = gql(QUERY, {"login": LOGIN, "cursor": cursor}, token)["user"]["repositories"]
        for repo in data["nodes"]:
            edges = repo["languages"]["edges"]
            if edges:
                repos += 1
            for edge in edges:
                node = edge["node"]
                entry = totals.setdefault(
                    node["name"],
                    {"size": 0, "color": PALETTE.get(node["name"], node["color"] or "#8B949E")},
                )
                entry["size"] += edge["size"]
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    ranked = sorted(totals.items(), key=lambda kv: kv[1]["size"], reverse=True)
    top = [(name, meta["size"], meta["color"]) for name, meta in ranked[:TOP_N]]
    rest = sum(meta["size"] for _, meta in ranked[TOP_N:])
    total = sum(meta["size"] for _, meta in ranked)
    if rest:
        top.append(("Other", rest, "#8B949E"))
    return {"languages": top, "total": total, "repos": repos}


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def human_bytes(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB" if n >= 1_000_000 else f"{n / 1_000:.0f} kB"


def pretty(name: str) -> str:
    return "C++" if name == "C++" else name


def render(d: dict, theme: str) -> str:
    t = THEMES[theme]

    x0, bar_w, bar_y, bar_h = 56, 888, 66, 26
    gap = 3.0
    total = d["total"] or 1
    langs = d["languages"]
    usable = bar_w - gap * (len(langs) - 1)

    segments = []
    x = x0
    for name, size, color in langs:
        width = max(4.0, usable * size / total)
        segments.append(
            f'      <rect x="{x:.1f}" y="{bar_y}" width="{width:.1f}" height="{bar_h}" rx="4" fill="{color}">'
            f'<title>{esc(name)} — {size / total * 100:.1f}%</title></rect>'
        )
        x += width + gap

    # legend: four columns, name on the left, share on the right
    col_w = bar_w / 4
    legend = []
    for i, (name, size, color) in enumerate(langs):
        row, col = divmod(i, 4)
        cx = x0 + col * col_w
        cy = 136 + row * 34
        pct = size / total * 100
        legend.append(
            f'      <circle cx="{cx + 5:.1f}" cy="{cy - 4:.1f}" r="5" fill="{color}"/>'
            f'<text x="{cx + 19:.1f}" y="{cy}" font-family="{MONO}" font-size="12.5" fill="{t["text_soft"]}">{esc(pretty(name))}</text>'
            f'<text x="{cx + col_w - 26:.1f}" y="{cy}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{t["muted"]}">'
            f'{pct:.1f}%</text>'
        )

    segments_svg = "\n".join(segments)
    legend_svg = "\n".join(legend)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="lt">
  <title id="lt">Language split across {d['repos']} public repositories: {', '.join(f'{n} {s / total * 100:.0f}%' for n, s, _ in langs)}</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{t['bg0']}"/><stop offset="1" stop-color="{t['bg1']}"/>
    </linearGradient>
    <radialGradient id="glowA" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{t['amber']}" stop-opacity="{t['amber_op']}"/>
      <stop offset="1" stop-color="{t['amber']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{t['blue']}" stop-opacity="{t['blue_op']}"/>
      <stop offset="1" stop-color="{t['blue']}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="dots" width="21" height="21" patternUnits="userSpaceOnUse">
      <circle cx="1.5" cy="1.5" r="1.05" fill="{t['dot']}" fill-opacity="{t['dot_op']}"/>
    </pattern>
    <clipPath id="frame"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18"/></clipPath>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#dots)"/>
    <ellipse cx="60" cy="10" rx="300" ry="150" fill="url(#glowA)"/>
    <ellipse cx="950" cy="{H}" rx="300" ry="150" fill="url(#glowB)"/>

    <text x="{x0}" y="44" font-family="{MONO}" font-size="11" letter-spacing="3.2" fill="{t['amber']}">LANGUAGES &#183; PUBLIC REPOS</text>
    <text x="{x0 + bar_w}" y="44" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t['label']}">
      {d['repos']} repos &#183; {human_bytes(total)} of code
    </text>

{segments_svg}
{legend_svg}

    <path d="M{x0} 196 h{bar_w}" stroke="{t['hair']}" stroke-width="1"/>
    <text x="{x0}" y="216" font-family="{MONO}" font-size="9.5" fill="{t['label']}">bytes per language, from the GitHub API &#183; top {TOP_N} + other</text>
  </g>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="none" stroke="{t['border']}" stroke-width="1"/>
</svg>
"""


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN (a token with read access to the GraphQL API).")

    data = collect(token)
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = OUT / f"langs-{theme}.svg"
        path.write_text(render(data, theme), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} B)")

    print(", ".join(f"{n}={s / data['total'] * 100:.1f}%" for n, s, _ in data["languages"]))


if __name__ == "__main__":
    main()
