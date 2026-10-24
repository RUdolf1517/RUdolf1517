#!/usr/bin/env python3
"""Render the commit-activity card for the profile README.

Pulls the last 12 months of contribution data from the GitHub GraphQL API and
writes two theme-matched SVG files:

    assets/commits-dark.svg
    assets/commits-light.svg

Standard library only, so the workflow needs no pip install:

    GITHUB_TOKEN=... python3 scripts/gen_stats.py

The workflow runs it weekly; running it by hand is fine too.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("PROFILE_LOGIN", "RUdolf1517")
API = "https://api.github.com/graphql"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

from theme import MONO, SANS, THEMES  # noqa: E402

W, H = 1000, 250
MONTHS_BACK = 12


# ---------------------------------------------------------------- data fetching

def gql(query: str, variables: dict, token: str) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-card",
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


YEAR_QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      totalRepositoriesWithContributedCommits
      commitContributionsByRepository(maxRepositories:10) {
        repository { nameWithOwner }
        contributions(first:1) { totalCount }
      }
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

MONTH_QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) { totalCommitContributions }
  }
}
"""


def month_bounds(year: int, month: int) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime(year, month, 1, tzinfo=dt.timezone.utc)
    end = (start.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(seconds=1)
    return start, end


def previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def first_month_of_window(today: dt.date, months: int = MONTHS_BACK) -> tuple[int, int]:
    """First month of the trailing window, so totals and bars cover the same span."""
    index = today.year * 12 + (today.month - 1) - (months - 1)
    return index // 12, index % 12 + 1


def collect(token: str, today: dt.date) -> dict:
    start, _ = month_bounds(*first_month_of_window(today))
    end = dt.datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=dt.timezone.utc)
    data = gql(YEAR_QUERY, {
        "login": LOGIN,
        "from": start.isoformat().replace("+00:00", "Z"),
        "to": end.isoformat().replace("+00:00", "Z"),
    }, token)["user"]["contributionsCollection"]

    days = [
        (d["date"], d["contributionCount"])
        for week in data["contributionCalendar"]["weeks"]
        for d in week["contributionDays"]
    ]
    days.sort()
    active_days = sum(1 for _, count in days if count > 0)
    busiest_date, busiest_count = max(days, key=lambda x: x[1], default=(None, 0))

    longest = current = 0
    for _, count in days:
        current = current + 1 if count > 0 else 0
        longest = max(longest, current)
    # trailing streak: walk back from the newest day
    trailing = 0
    for _, count in reversed(days):
        if count == 0:
            break
        trailing += 1

    months = []
    year, month = start.year, start.month
    while (year, month) <= (today.year, today.month):
        m_start, m_end = month_bounds(year, month)
        commits = gql(MONTH_QUERY, {
            "login": LOGIN,
            "from": m_start.isoformat().replace("+00:00", "Z"),
            "to": min(m_end, end).isoformat().replace("+00:00", "Z"),
        }, token)["user"]["contributionsCollection"]["totalCommitContributions"]
        months.append((year, month, commits))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

    repos = sorted(
        ((r["repository"]["nameWithOwner"], r["contributions"]["totalCount"])
         for r in data["commitContributionsByRepository"]),
        key=lambda r: r[1],
        reverse=True,
    )

    return dict(
        commits=data["totalCommitContributions"],
        prs=data["totalPullRequestContributions"],
        issues=data["totalIssueContributions"],
        reviews=data["totalPullRequestReviewContributions"],
        repos=data["totalRepositoriesWithContributedCommits"],
        active_days=active_days,
        longest_streak=longest,
        current_streak=trailing,
        busiest_date=busiest_date,
        busiest_count=busiest_count,
        months=months,
        top_repos=repos,
        updated=today.isoformat(),
    )


# --------------------------------------------------------------------- rendering

def nf(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def human_date(iso: str | None) -> str:
    if not iso:
        return "—"
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')}"


def stat_block(x: float, value: int, label: str, t: dict) -> str:
    return f"""    <text x="{x}" y="132" font-family="{SANS}" font-size="42" font-weight="700" letter-spacing="-1" fill="{t['text']}">{nf(value)}</text>
    <text x="{x + 1}" y="152" font-family="{MONO}" font-size="10.5" letter-spacing="1.7" fill="{t['label']}">{label}</text>"""


def render(d: dict, name: str) -> str:
    t = THEMES[name]

    chart_x, chart_w, chart_base, chart_h = 560, 384, 186, 100
    bars = d["months"]
    gap = 9
    bar_w = (chart_w - gap * (len(bars) - 1)) / len(bars)
    peak = max((c for *_, c in bars), default=1) or 1

    bar_svg = []
    for i, (year, month, commits) in enumerate(bars):
        x = chart_x + i * (bar_w + gap)
        is_current = i == len(bars) - 1
        h = max(2.5, chart_h * commits / peak) if commits else 2.5
        y = chart_base - h
        fill = t["stub"] if commits == 0 else (t["bar_accent"] if is_current else t["bar"])
        rx = min(3, h / 2)
        bar_svg.append(
            f'      <rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="{rx:.1f}" fill="{fill}">'
            f'<title>{commits} commits · {dt.date(year, month, 1).strftime("%B %Y")}</title></rect>'
        )
        if commits:
            bar_svg.append(
                f'      <text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" '
                f'font-family="{MONO}" font-size="9.5" fill="{t["muted"]}">{commits}</text>'
            )
        bar_svg.append(
            f'      <text x="{x + bar_w / 2:.1f}" y="{chart_base + 17}" text-anchor="middle" '
            f'font-family="{MONO}" font-size="9.5" fill="{t["label"]}">'
            f'{dt.date(year, month, 1).strftime("%b")}</text>'
        )

    facts = "  ·  ".join([
        f'{d["active_days"]} active days',
        f'longest streak {d["longest_streak"]} d',
        f'busiest day {d["busiest_count"]} ({human_date(d["busiest_date"])})',
    ])

    top_repo_line = ""
    if d["top_repos"]:
        repo, count = d["top_repos"][0]
        muted = t["muted"]
        top_repo_line = (
            f'    <text x="56" y="212" font-family="{MONO}" font-size="11" fill="{muted}">'
            f'most active: {repo.split("/")[-1]} — {count} commits</text>'
        )

    bars_svg = "\n".join(bar_svg)

    first = dt.date(bars[0][0], bars[0][1], 1)
    last = dt.date(bars[-1][0], bars[-1][1], 1)
    span = f'{first.strftime("%b %Y")} → {last.strftime("%b %Y")}'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="stitle">
  <title id="stitle">Commit activity for {LOGIN}: {d['commits']} commits and {d['prs']} pull requests over the last 12 months</title>
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
    <ellipse cx="40" cy="20" rx="300" ry="190" fill="url(#glowA)"/>
    <ellipse cx="960" cy="240" rx="300" ry="180" fill="url(#glowB)"/>

    <text x="56" y="46" font-family="{MONO}" font-size="11" letter-spacing="3.2" fill="{t['amber']}">COMMITS &#183; LAST 12 MONTHS</text>
{stat_block(56, d['commits'], 'COMMITS', t)}
{stat_block(224, d['prs'], 'PULL REQUESTS', t)}
{stat_block(392, d['repos'], 'REPOSITORIES', t)}
    <path d="M212 74 v82" stroke="{t['hair']}" stroke-width="1"/>
    <path d="M380 74 v82" stroke="{t['hair']}" stroke-width="1"/>
    <text x="56" y="190" font-family="{MONO}" font-size="11" fill="{t['muted']}">{facts}</text>
{top_repo_line}
    <text x="56" y="236" font-family="{MONO}" font-size="9.5" fill="{t['label']}">updated {d['updated']}</text>

    <text x="{chart_x}" y="46" font-family="{MONO}" font-size="10.5" letter-spacing="2.6" fill="{t['label']}">COMMIT ACTIVITY</text>
    <text x="{chart_x + chart_w}" y="46" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{t['label']}">{span}</text>
{bars_svg}
    <path d="M{chart_x} {chart_base + 0.5} h{chart_w}" stroke="{t['hair']}" stroke-width="1"/>
    <text x="{chart_x + chart_w}" y="232" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{t['label']}">commits per month</text>
  </g>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="none" stroke="{t['border']}" stroke-width="1"/>
</svg>
"""


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN (a token with read access to the GraphQL API).")

    today = dt.date.today()
    data = collect(token, today)

    OUT.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = OUT / f"commits-{theme}.svg"
        path.write_text(render(data, theme), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} B)")

    print(f"commits={data['commits']} prs={data['prs']} repos={data['repos']} "
          f"active_days={data['active_days']} longest={data['longest_streak']}")


if __name__ == "__main__":
    main()
