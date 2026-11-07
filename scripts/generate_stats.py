
#!/usr/bin/env python3
"""Generate assets/stats.svg from the GitHub API (no third-party service needed).

Env: GH_USER (default: repository owner), GITHUB_TOKEN (optional but recommended).
"""
import json, os, sys, urllib.request, urllib.parse
from collections import Counter

USER = os.environ.get("GH_USER", "hocineguelaache-cmd")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "stats.svg")
GOLD = "#F7C936"
LANG_COLORS = {"Java": "#b07219", "PHP": "#4F5D95", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
               "Python": "#3572A5", "HTML": "#e34c26", "CSS": "#563d7c", "Vue": "#41b883", "C": "#555555",
               "C++": "#f34b7d", "SQL": "#e38c00", "PLpgSQL": "#336790", "Shell": "#89e051", "TeX": "#3D6117"}


def api(path, data=None):
    req = urllib.request.Request("https://api.github.com" + path, data=data)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-stats")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def safe(fn, default=None):
    try:
        return fn()
    except Exception as e:  # keep the card alive even if one call fails
        print("warn:", e, file=sys.stderr)
        return default


def collect():
    user = api(f"/users/{USER}")
    repos = []
    page = 1
    while True:
        chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in own)
    langs = Counter()
    for r in own:
        d = safe(lambda: api(f"/repos/{USER}/{r['name']}/languages"), {})
        langs.update(d)
    q = lambda s: urllib.parse.quote(s)
    commits = safe(lambda: api(f"/search/commits?q={q('author:' + USER)}&per_page=1")["total_count"])
    prs = safe(lambda: api(f"/search/issues?q={q(f'author:{USER} type:pr')}&per_page=1")["total_count"])
    contrib = None
    if TOKEN:
        gql = json.dumps({"query": 'query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions}}}}',
                          "variables": {"l": USER}}).encode()
        contrib = safe(lambda: api("/graphql", gql)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"])
    return {"repos": user["public_repos"], "stars": stars, "followers": user["followers"],
            "commits": commits, "prs": prs, "contrib": contrib, "langs": langs}


def fmt(v):
    return "–" if v is None else f"{v:,}".replace(",", " ")


def render(s):
    metrics = [("Public repos", s["repos"]), ("Stars earned", s["stars"]), ("Followers", s["followers"]),
               ("Commits (total)", s["commits"]), ("Pull requests", s["prs"]),
               ("Contributions (12 mo)", s["contrib"])]
    cells = ""
    for i, (label, val) in enumerate(metrics):
        x = 40 + (i % 3) * 150
        y = 96 + (i // 3) * 74
        cells += (f'<text x="{x}" y="{y}" font-size="28" font-weight="700" fill="#f0f6fc">{fmt(val)}</text>'
                  f'<text x="{x}" y="{y + 20}" font-size="11" letter-spacing="1" fill="#7d8590">{label.upper()}</text>')
    total = sum(s["langs"].values()) or 1
    top = s["langs"].most_common(6)
    bar, legend, x0 = "", "", 520
    bw = 340
    for i, (name, n) in enumerate(top):
        w = max(bw * n / total, 2)
        c = LANG_COLORS.get(name, "#8b949e")
        bar += f'<rect x="{x0:.1f}" y="76" width="{w:.1f}" height="10" fill="{c}"/>'
        x0 += w
        ly = 118 + (i % 3) * 24
        lx = 520 + (i // 3) * 175
        legend += (f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{c}"/>'
                   f'<text x="{lx + 18}" y="{ly}" font-size="13" fill="#e6edf3">{name}</text>'
                   f'<text x="{lx + 150}" y="{ly}" font-size="12" text-anchor="end" fill="#7d8590">{100 * n / total:.0f}%</text>')
    if not top:
        legend = '<text x="520" y="118" font-size="13" fill="#7d8590">Updated automatically by GitHub Actions</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 230" width="900" height="230" role="img" aria-label="GitHub statistics for {USER}">
<g font-family="-apple-system,'Segoe UI',Helvetica,Arial,sans-serif">
<rect width="900" height="230" rx="16" fill="#0d1117"/>
<rect width="5" height="230" fill="{GOLD}"/>
<text x="40" y="44" font-size="11" font-weight="600" letter-spacing="2.2" fill="#7d8590">GITHUB STATISTICS</text>
<text x="520" y="44" font-size="11" font-weight="600" letter-spacing="2.2" fill="#7d8590">TOP LANGUAGES</text>
<rect x="40" y="52" width="40" height="2" fill="{GOLD}"/><rect x="520" y="52" width="40" height="2" fill="{GOLD}"/>
{cells}
<g clip-path="inset(0 round 5px)"><rect x="520" y="76" width="340" height="10" rx="5" fill="#161b22"/>{bar}</g>
{legend}
<rect x=".5" y=".5" width="899" height="229" rx="16" fill="none" stroke="#30363d"/>
</g></svg>'''


if __name__ == "__main__":
    stats = collect() if "--empty" not in sys.argv else {
        "repos": None, "stars": None, "followers": None, "commits": None, "prs": None, "contrib": None, "langs": Counter()}
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print("stats.svg written")
