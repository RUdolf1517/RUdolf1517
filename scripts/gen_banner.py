#!/usr/bin/env python3
"""Generate the profile banner (light + dark) as static SVG.

Geometry is tuned for GitHub's ~880px content column: the banner is 1000px wide,
so it scales almost 1:1 and the 12.5px terminal type stays legible.

    python3 scripts/gen_banner.py

Writes assets/banner-dark.svg and assets/banner-light.svg.
"""

from __future__ import annotations

from pathlib import Path

W, H = 1000, 330

from theme import HEB, MONO, SANS, THEMES  # noqa: E402

PX = 56
TX, TY, TW, TH = 576, 78, 368, 170
EYEBROW_Y = 78
NAME_Y, TAG_Y = 138, 178
RULE_Y = 200
PROVERB_Y, TRANSLIT_Y = 224, 247
PILL_Y = 264

# Yiddish proverb: "a person plans, and God laughs" (Wikiquote / Furman 1968)
PROVERB = "דער מענטש טראַכט און גאָט לאַכט"
PROVERB_TR = "Der mentsh trakht un Got lakht — a person plans, and God laughs"
PROVERB_CENTER = 203  # left edge at PX, anchored in the middle so direction never clips it


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pill(x: float, y: float, text: str, t: dict) -> tuple[str, float]:
    pad, dot_w, size = 14, 14, 12.0
    w = pad * 2 + dot_w + len(text) * size * 0.66
    h = 28
    svg = f"""    <g>
      <rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{t['pill_bg']}" stroke="{t['pill_border']}" stroke-width="1"/>
      <circle cx="{x + pad:.1f}" cy="{y + h / 2}" r="3" fill="{t['term_amber']}"/>
      <text x="{x + pad + dot_w + (w - pad * 2 - dot_w) / 2:.1f}" y="{y + h / 2 + 4.1}" text-anchor="middle" font-family="{MONO}" font-size="{size}" fill="{t['pill_text']}">{esc(text)}</text>
    </g>"""
    return svg, w


def banner(name: str) -> str:
    t = THEMES[name]
    x = PX
    pills = []
    for label in ("tummler", "KOMP", "bulboz"):
        svg, w = pill(x, PILL_Y, label, t)
        pills.append(svg)
        x += w + 9

    lines = [
        (f'<tspan fill="{t["term_amber"]}">$</tspan> <tspan fill="{t["term_text"]}">tummler photo.png webp</tspan>', 64),
        (f'<tspan fill="{t["term_green"]}">12 files · 48 MB → 11 MB</tspan> <tspan fill="{t["term_muted"]}">(−77%)</tspan>', 85),
        (f'<tspan fill="{t["term_amber"]}">$</tspan> <tspan fill="{t["term_text"]}">komp --listen</tspan>', 122),
        (f'<tspan fill="{t["term_muted"]}">wake word</tspan> <tspan fill="{t["term_text"]}">«комп»</tspan>  <tspan fill="{t["term_green"]}">●</tspan> <tspan fill="{t["term_muted"]}">ready</tspan>', 143),
    ]
    term_lines = "\n".join(
        f'      <text x="{TX + 24}" y="{TY + dy}" font-family="{MONO}" font-size="12.5" xml:space="preserve" '
        f'direction="ltr">{line}</text>'
        for line, dy in lines
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">Rudolf Zinovev — systems and web developer</title>
  <desc id="d">Banner with a Yiddish proverb — a person plans, and God laughs — and a terminal demoing the tummler converter CLI and the KOMP voice assistant.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{t['bg0']}"/><stop offset="1" stop-color="{t['bg1']}"/>
    </linearGradient>
    <linearGradient id="name" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{t['name_from']}"/><stop offset="1" stop-color="{t['name_to']}"/>
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
    <clipPath id="frame"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="22"/></clipPath>
    <filter id="lift" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="9" stdDeviation="13" flood-color="{t['shadow']}" flood-opacity="{t['shadow_op']}"/>
    </filter>
    <style>
      .caret {{ animation: blink 1.15s steps(1, end) infinite; }}
      .pulse {{ animation: pulse 3.6s ease-in-out infinite; }}
      @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
      @keyframes pulse {{ 0%, 100% {{ opacity: 0.35; }} 50% {{ opacity: 0.9; }} }}
      @media (prefers-reduced-motion: reduce) {{ .caret, .pulse {{ animation: none; }} }}
    </style>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#dots)"/>
    <ellipse cx="110" cy="-10" rx="380" ry="250" fill="url(#glowA)"/>
    <ellipse cx="930" cy="{H + 10}" rx="340" ry="230" fill="url(#glowB)"/>
    <rect width="{W}" height="2.4" fill="url(#name)" opacity="0.85"/>

    <circle class="pulse" cx="{PX + 3}" cy="{EYEBROW_Y - 4}" r="4.2" fill="{t['amber']}"/>
    <text x="{PX + 17}" y="{EYEBROW_Y}" font-family="{MONO}" font-size="11" letter-spacing="3.4" fill="{t['eyebrow']}">HELLO, I&#8217;M</text>

    <text x="{PX - 2}" y="{NAME_Y}" font-family="{SANS}" font-size="54" font-weight="700" letter-spacing="-1.3" fill="url(#name)">Rudolf Zinovev</text>
    <text x="{PX}" y="{TAG_Y}" font-family="{SANS}" font-size="18" fill="{t['tagline']}">Systems &amp; web developer — small tools, sharp edges.</text>

    <path d="M{PX} {RULE_Y} h30" stroke="{t['amber']}" stroke-width="2" stroke-linecap="round" opacity="0.85"/>
    <text x="{PROVERB_CENTER}" y="{PROVERB_Y}" font-family="{HEB}" font-size="20" fill="{t['proverb']}" direction="rtl" text-anchor="middle" xml:space="preserve">{esc(PROVERB)}</text>
    <text x="{PX}" y="{TRANSLIT_Y}" font-family="{MONO}" font-size="10.5" fill="{t['proverb_tr']}">{esc(PROVERB_TR)}</text>

{"".join(pills)}

    <g filter="url(#lift)">
      <rect x="{TX}" y="{TY}" width="{TW}" height="{TH}" rx="14" fill="{t['term_bg']}" stroke="{t['term_border']}" stroke-width="1"/>
    </g>
    <path d="M{TX} {TY + 33} h{TW}" stroke="{t['term_border']}" stroke-width="1"/>
    <circle cx="{TX + 21}" cy="{TY + 16.5}" r="4" fill="#FF5F57" opacity="0.92"/>
    <circle cx="{TX + 38}" cy="{TY + 16.5}" r="4" fill="#FEBC2E" opacity="0.92"/>
    <circle cx="{TX + 55}" cy="{TY + 16.5}" r="4" fill="#28C840" opacity="0.92"/>
    <text x="{TX + TW - 18}" y="{TY + 20}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{t['term_muted']}">zsh</text>
{term_lines}
    <rect class="caret" x="{TX + 215}" y="{TY + 137}" width="6" height="13.5" fill="{t['term_amber']}" opacity="0.9"/>
  </g>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="22" fill="none" stroke="{t['border']}" stroke-width="1"/>
</svg>
"""


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = out / f"banner-{theme}.svg"
        path.write_text(banner(theme), encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size} B)")


if __name__ == "__main__":
    main()
