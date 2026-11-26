"""Generate GitHub Stats and Top Languages SVG cards via GitHub GraphQL API."""

import html
import json
import os
import subprocess
import urllib.request

USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "abdulrahmontim")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "title": "#58a6ff",
        "text": "#c9d1d9",
        "icon": "#1f6feb",
        "ring_bg": "#30363d",
    },
    "light": {
        "bg": "#fffefe",
        "title": "#2f80ed",
        "text": "#434d58",
        "icon": "#4c71f2",
        "ring_bg": "#e4e2e2",
    },
}

ICONS = {
    "star": '<path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25zm0 2.445L6.615 5.5a.75.75 0 01-.564.41l-3.097.45 2.24 2.184a.75.75 0 01.216.664l-.528 3.084 2.769-1.456a.75.75 0 01.698 0l2.77 1.456-.53-3.084a.75.75 0 01.216-.664l2.24-2.183-3.096-.45a.75.75 0 01-.564-.41L8 2.694v.001z"/>',
    "commits": '<path fill-rule="evenodd" d="M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z"/>',
    "prs": '<path fill-rule="evenodd" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"/>',
    "issues": '<path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z"/>',
    "contribs": '<path fill-rule="evenodd" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"/>',
}


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    proc = subprocess.Popen(
        ["git", "credential", "fill"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, _ = proc.communicate("protocol=https\nhost=github.com\n")
    for line in stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise RuntimeError("No GitHub token found in environment or git credential helper")


def fetch_github_data(token: str, username: str) -> dict:
    query = """
    query($login: String!) {
      user(login: $login) {
        name
        login
        followers { totalCount }
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
        }
        pullRequests(first: 1) { totalCount }
        issues(first: 1) { totalCount }
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {direction: DESC, field: STARGAZERS}) {
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8"),
        headers={"Authorization": f"bearer {token}", "User-Agent": "github-stats-generator"},
    )
    res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    if "errors" in res:
        raise RuntimeError(f"GraphQL error: {res['errors']}")
    return res["data"]["user"]


def calculate_rank(commits: int, prs: int, issues: int, stars: int, followers: int, reviews: int = 0) -> tuple[str, float]:
    def exp_cdf(x: float) -> float:
        return 1.0 - (2.0 ** -x)

    def log_norm_cdf(x: float) -> float:
        return x / (1.0 + x)

    total_weight = 12.0
    rank = 1.0 - (
        2.0 * exp_cdf(commits / 250.0)
        + 3.0 * exp_cdf(prs / 50.0)
        + 1.0 * exp_cdf(issues / 25.0)
        + 1.0 * exp_cdf(reviews / 2.0)
        + 4.0 * log_norm_cdf(stars / 50.0)
        + 1.0 * log_norm_cdf(followers / 10.0)
    ) / total_weight

    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    pct = rank * 100.0
    for threshold, level in zip(thresholds, levels):
        if pct <= threshold:
            return level, pct
    return "C", pct


def k_format(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def build_stats_svg(user: dict, theme: dict) -> str:
    name = html.escape(user.get("name") or user["login"])
    title = f"{name}'s GitHub Stats"
    stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
    cc = user["contributionsCollection"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = user["pullRequests"]["totalCount"]
    issues = user["issues"]["totalCount"]
    contribs = user["repositoriesContributedTo"]["totalCount"]
    followers = user["followers"]["totalCount"]

    level, pct = calculate_rank(commits, prs, issues, stars, followers)
    progress = max(0.0, min(100.0, 100.0 - pct))
    circumference = 251.327
    dashoffset = circumference * (1.0 - progress / 100.0)

    rows = [
        ("star", "Total Stars Earned:", k_format(stars)),
        ("commits", "Total Commits (last year):", k_format(commits)),
        ("prs", "Total PRs:", k_format(prs)),
        ("issues", "Total Issues:", k_format(issues)),
        ("contribs", "Contributed to (last year):", k_format(contribs)),
    ]

    row_svg = []
    for idx, (icon_key, label, value) in enumerate(rows):
        y = idx * 25
        row_svg.append(
            f'<g transform="translate(0, {y})">'
            f'<svg x="25" y="0" width="16" height="16" viewBox="0 0 16 16" fill="{theme["icon"]}">{ICONS[icon_key]}</svg>'
            f'<text x="50" y="12.5" class="stat bold">{html.escape(label)}</text>'
            f'<text x="240" y="12.5" class="stat bold">{html.escape(value)}</text>'
            f"</g>"
        )

    return f"""<svg width="450" height="195" viewBox="0 0 450 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(title)}">
  <title>{html.escape(title)}</title>
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {theme['title']}; }}
    .stat {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {theme['text']}; }}
    .bold {{ font-weight: 700; }}
    .rank-text {{ font: 800 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: {theme['text']}; }}
  </style>
  <rect x="0.5" y="0.5" rx="4.5" width="449" height="194" fill="{theme['bg']}"/>
  <g transform="translate(25, 35)">
    <text x="0" y="0" class="header">{html.escape(title)}</text>
  </g>
  <g transform="translate(0, 55)">
    {''.join(row_svg)}
  </g>
  <g transform="translate(365, 115)">
    <circle cx="0" cy="0" r="40" fill="none" stroke="{theme['ring_bg']}" stroke-width="6"/>
    <circle cx="0" cy="0" r="40" fill="none" stroke="{theme['title']}" stroke-width="6"
            stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{dashoffset:.2f}"
            stroke-linecap="round" transform="rotate(-90)"/>
    <text x="0" y="8" text-anchor="middle" class="rank-text">{html.escape(level)}</text>
  </g>
</svg>
"""


def build_langs_svg(user: dict, theme: dict) -> str:
    totals: dict[str, dict] = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            lang = edge["node"]["name"]
            color = edge["node"]["color"] or "#858585"
            if lang not in totals:
                totals[lang] = {"size": 0, "color": color}
            totals[lang]["size"] += edge["size"]

    sorted_langs = sorted(totals.items(), key=lambda kv: kv[1]["size"], reverse=True)[:6]
    total_bytes = sum(v["size"] for _, v in sorted_langs) or 1

    bar_width = 250.0
    bar_segments = []
    x_offset = 0.0
    for lang, info in sorted_langs:
        w = (info["size"] / total_bytes) * bar_width
        bar_segments.append(
            f'<rect x="{x_offset:.2f}" y="0" width="{w:.2f}" height="8" fill="{info["color"]}"/>'
        )
        x_offset += w

    legend_items = []
    for idx, (lang, info) in enumerate(sorted_langs):
        col = idx % 2
        row = idx // 2
        tx = 25 + col * 130
        ty = row * 25
        pct = (info["size"] / total_bytes) * 100.0
        legend_items.append(
            f'<g transform="translate({tx}, {ty})">'
            f'<circle cx="5" cy="6" r="5" fill="{info["color"]}"/>'
            f'<text x="15" y="10" class="lang-name">{html.escape(lang)} {pct:.2f}%</text>'
            f"</g>"
        )

    height = 95 + ((len(sorted_langs) + 1) // 2) * 25
    return f"""<svg width="300" height="{height}" viewBox="0 0 300 {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Most Used Languages">
  <title>Most Used Languages</title>
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {theme['title']}; }}
    .lang-name {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {theme['text']}; }}
  </style>
  <defs>
    <clipPath id="bar-clip"><rect x="0" y="0" width="{int(bar_width)}" height="8" rx="4"/></clipPath>
  </defs>
  <rect x="0.5" y="0.5" rx="4.5" width="299" height="{height - 1}" fill="{theme['bg']}"/>
  <g transform="translate(25, 35)">
    <text x="0" y="0" class="header">Most Used Languages</text>
  </g>
  <g transform="translate(25, 55)" clip-path="url(#bar-clip)">
    {''.join(bar_segments)}
  </g>
  <g transform="translate(0, 80)">
    {''.join(legend_items)}
  </g>
</svg>
"""


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    token = get_token()
    user = fetch_github_data(token, USERNAME)

    for mode, theme in THEMES.items():
        with open(os.path.join(OUT_DIR, f"stats-{mode}.svg"), "w", encoding="utf-8") as f:
            f.write(build_stats_svg(user, theme))
        with open(os.path.join(OUT_DIR, f"langs-{mode}.svg"), "w", encoding="utf-8") as f:
            f.write(build_langs_svg(user, theme))

    print(f"Generated 4 SVG cards in {OUT_DIR} for {USERNAME}")


if __name__ == "__main__":
    main()
