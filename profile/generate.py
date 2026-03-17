#!/usr/bin/env python3
import json
import os
import re
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config" / "config.json"
TEMPLATES_DIR = SCRIPT_DIR / "templates"


def load_config():
    return json.loads(CONFIG_PATH.read_text())


def github_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lohith-profile-generator",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_text(url):
    request = Request(url, headers=github_headers())
    with urlopen(request) as response:
        return response.read().decode("utf-8", "ignore")


def fetch_json(url):
    return json.loads(fetch_text(url))


def fetch_all_json(url):
    page = 1
    items = []
    while True:
        page_items = fetch_json(f"{url}{'&' if '?' in url else '?'}per_page=100&page={page}")
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < 100:
            break
        page += 1
    return items


def fetch_json_status(url):
    request = Request(url, headers=github_headers(), method="GET")
    try:
        with urlopen(request) as response:
            response.read()
            return response.status
    except Exception as exc:
        status = getattr(exc, "code", None)
        if status is not None:
            return status
        raise


def parse_public_activity(username):
    html = fetch_text(f"https://github.com/users/{username}/contributions")

    total_match = re.search(r"([0-9,]+)\s+contributions?\s+in the last year", html, re.I)
    total_contributions = int(total_match.group(1).replace(",", "")) if total_match else 0

    day_matches = re.findall(r'data-date="([0-9-]+)".*?data-level="([0-4])"', html)
    active_dates = sorted(
        date.fromisoformat(day)
        for day, level in day_matches
        if level != "0"
    )

    if not active_dates:
        return {
            "total_contributions": total_contributions,
            "active_days": 0,
            "current_streak": 0,
            "best_streak": 0,
        }

    best_streak = 1
    current_run = 1
    for previous, current in zip(active_dates, active_dates[1:]):
        if current == previous + timedelta(days=1):
            current_run += 1
            best_streak = max(best_streak, current_run)
        else:
            current_run = 1

    current_streak = 1
    for index in range(len(active_dates) - 1, 0, -1):
        if active_dates[index] == active_dates[index - 1] + timedelta(days=1):
            current_streak += 1
        else:
            break

    return {
        "total_contributions": total_contributions,
        "active_days": len(active_dates),
        "current_streak": current_streak,
        "best_streak": best_streak,
    }


def fetch_public_stats(username):
    user = fetch_json(f"https://api.github.com/users/{username}")
    repos = fetch_all_json(
        f"https://api.github.com/users/{username}/repos?type=owner&sort=updated"
    )
    orgs = fetch_json(f"https://api.github.com/users/{username}/orgs")
    activity = parse_public_activity(username)

    public_repos = [repo for repo in repos if not repo.get("fork")]
    total_stars = sum(repo.get("stargazers_count", 0) for repo in public_repos)

    languages = {}
    for repo in public_repos:
        repo_languages = fetch_json(repo["languages_url"])
        for language, amount in repo_languages.items():
            languages[language] = languages.get(language, 0) + amount

    total_language_bytes = sum(languages.values())
    top_languages = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:5]
    language_rows = []
    for language, amount in top_languages:
        percent = 0 if total_language_bytes == 0 else (amount / total_language_bytes) * 100
        language_rows.append({"name": language, "percent": percent})

    return {
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": len(public_repos),
        "public_orgs": len(orgs),
        "total_stars": total_stars,
        "languages": language_rows,
        **activity,
    }


def fetch_org_spotlights(config):
    orgs = []
    for org in config.get("org_spotlight", []):
        login = org["login"]
        org_data = fetch_json(f"https://api.github.com/orgs/{login}")
        repos = fetch_all_json(
            f"https://api.github.com/orgs/{login}/repos?type=public&sort=updated"
        )
        top_repo = max(repos, key=lambda item: item.get("stargazers_count", 0), default=None)
        public_member_status = fetch_json_status(
            f"https://api.github.com/orgs/{login}/public_members/{config['username']}"
        )
        orgs.append(
            {
                "login": login,
                "label": org.get("label", login),
                "headline": org.get("headline", ""),
                "website": org.get("website") or org_data.get("blog") or "",
                "location": org_data.get("location") or "",
                "public_repos": org_data.get("public_repos", len(repos)),
                "followers": org_data.get("followers", 0),
                "public_membership": public_member_status == 204,
                "top_repo_name": top_repo["name"] if top_repo else "",
                "top_repo_url": top_repo["html_url"] if top_repo else "",
                "top_repo_desc": top_repo.get("description") or "" if top_repo else "",
                "top_repo_stars": top_repo.get("stargazers_count", 0) if top_repo else 0,
            }
        )
    return orgs


def empty_stats():
    return {
        "followers": 0,
        "following": 0,
        "public_repos": 0,
        "public_orgs": 0,
        "total_stars": 0,
        "languages": [],
        "total_contributions": 0,
        "active_days": 0,
        "current_streak": 0,
        "best_streak": 0,
    }


def parse_experience_row(row):
    company, role, period = (item.strip() for item in (row.split("//", 2) + ["", "", ""])[:3])
    return {
        "company": company,
        "role": role,
        "period": period,
    }


def build_context(config, stats):
    context = {
        "USERNAME": config["username"],
        "DISPLAY_NAME": config["display_name"],
        "TAGLINE": config["tagline"],
        "YEAR": str(datetime.now().year),
        "PUBLIC_CONTRIBUTIONS": str(stats["total_contributions"]),
        "ACTIVE_DAYS": str(stats["active_days"]),
        "CURRENT_STREAK": str(stats["current_streak"]),
        "BEST_STREAK": str(stats["best_streak"]),
        "PUBLIC_REPOS": str(stats["public_repos"]),
        "TOTAL_STARS": str(stats["total_stars"]),
        "FOLLOWERS": str(stats["followers"]),
        "FOLLOWING": str(stats["following"]),
        "PUBLIC_ORGS": str(stats["public_orgs"]),
    }
    context.update(config["theme"])

    for key, values in config.items():
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            continue
        for index, value in enumerate(values, start=1):
            context[f"{key.upper()}_{index}"] = value

    for index, row in enumerate(config.get("experience", []), start=1):
        parsed = parse_experience_row(row)
        context[f"EXPERIENCE_{index}_COMPANY"] = parsed["company"]
        context[f"EXPERIENCE_{index}_ROLE"] = parsed["role"]
        context[f"EXPERIENCE_{index}_PERIOD"] = parsed["period"]

    first_org = (config.get("org_spotlight") or [{}])[0]
    context["ORG_1_LABEL"] = first_org.get("label", "")
    context["ORG_1_HEADLINE"] = first_org.get("headline", "")
    context["ORG_1_WEBSITE"] = first_org.get("website", "").replace("https://", "")

    repo = config["repo"]
    context["SNAKE_LIGHT_URL"] = (
        f"https://raw.githubusercontent.com/{repo}/output/github-contribution-grid-snake.svg"
    )
    context["SNAKE_DARK_URL"] = (
        f"https://raw.githubusercontent.com/{repo}/output/github-contribution-grid-snake-dark.svg"
    )
    return context


def render_template(template_path, destination_path, context):
    content = template_path.read_text()
    for key in sorted(context, key=len, reverse=True):
        value = context[key]
        content = content.replace(f"{{{{{key}}}}}", value)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(content)
    print(f"generated {destination_path.relative_to(SCRIPT_DIR.parent)}")


def write_text_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"generated {path.relative_to(SCRIPT_DIR.parent)}")


def svg_style_block():
    return [
        "    <style>",
        '      .display { font-family: "Ubuntu Condensed", "Bebas Neue", "Oswald", "Impact", sans-serif; letter-spacing: 1.5px; font-weight: 700; }',
        '      .ui { font-family: "Ubuntu", "Inter", "SF Pro Display", "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-weight: 500; }',
        '      .mono { font-family: "Ubuntu Mono", "JetBrains Mono", "Fira Code", "SF Mono", "Consolas", monospace; letter-spacing: 0.35px; }',
        "    </style>",
    ]


def split_text(text, max_chars, max_lines=2):
    words = text.split()
    if not words:
        return [""] * max_lines

    lines = []
    current = []
    index = 0
    while index < len(words):
        word = words[index]
        candidate = " ".join(current + [word])
        if len(candidate) <= max_chars or not current:
            current.append(word)
            index += 1
            continue
        lines.append(" ".join(current))
        current = []
        if len(lines) == max_lines - 1:
            break

    remainder_words = words[index:]
    if current:
        remainder_words = current + remainder_words

    if remainder_words:
        remainder = " ".join(remainder_words)
        if len(remainder) > max_chars:
            remainder = remainder[: max_chars - 1].rstrip() + "…"
        lines.append(remainder)

    while len(lines) < max_lines:
        lines.append("")
    return lines[:max_lines]


def write_activity_svg(config, stats):
    theme = config["theme"]
    tiles = [
        ("Public Contributions", stats["total_contributions"], "last 12 months"),
        ("Active Days", stats["active_days"], "days with visible commits"),
        ("Current Streak", stats["current_streak"], "consecutive active days"),
        ("Best Streak", stats["best_streak"], "strongest visible run"),
    ]
    chips = [
        f"public repos {stats['public_repos']}",
        f"stars {stats['total_stars']}",
        f"followers {stats['followers']}",
        f"following {stats['following']}",
    ]
    tile_width = 214
    tile_gap = 18
    tile_xs = [42 + index * (tile_width + tile_gap) for index in range(4)]

    svg = [
        f'<svg viewBox="0 0 1000 332" xmlns="http://www.w3.org/2000/svg" width="1000" height="332" role="img" aria-label="Public activity summary for {escape(config["display_name"])}">',
        "  <defs>",
        '    <linearGradient id="panel-grad" x1="0" y1="0" x2="1" y2="1">',
        f'      <stop offset="0%" stop-color="#{theme["PANEL_SOFT"]}" />',
        f'      <stop offset="100%" stop-color="#{theme["PANEL"]}" />',
        "    </linearGradient>",
        '    <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">',
        f'      <stop offset="0%" stop-color="#{theme["ACCENT"]}" stop-opacity="0" />',
        f'      <stop offset="50%" stop-color="#{theme["ACCENT"]}" stop-opacity="0.34" />',
        f'      <stop offset="100%" stop-color="#{theme["ACCENT"]}" stop-opacity="0" />',
        "    </linearGradient>",
        '    <radialGradient id="tile-glow" cx="50%" cy="0%" r="90%">',
        f'      <stop offset="0%" stop-color="#{theme["ACCENT"]}" stop-opacity="0.12" />',
        f'      <stop offset="100%" stop-color="#{theme["ACCENT"]}" stop-opacity="0" />',
        "    </radialGradient>",
        '    <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">',
        f'      <path d="M28 0H0V28" fill="none" stroke="#{theme["EDGE_SOFT"]}" stroke-width="1" opacity="0.24" />',
        "    </pattern>",
        '    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">',
        '      <rect width="4" height="2" fill="#000000" opacity="0.06" />',
        "    </pattern>",
        *svg_style_block(),
        "  </defs>",
        f'  <rect width="1000" height="332" fill="#{theme["BG"]}" />',
        f'  <rect x="24" y="18" width="952" height="296" rx="20" fill="url(#panel-grad)" stroke="#{theme["EDGE"]}" stroke-opacity="0.6" />',
        '  <rect x="24" y="18" width="952" height="296" rx="20" fill="url(#grid)" opacity="0.12" />',
        '  <rect x="24" y="18" width="952" height="296" rx="20" fill="url(#scan)" opacity="0.28" />',
        f'  <text x="44" y="50" class="mono" fill="#{theme["ACCENT"]}" font-size="12">BATCOMPUTER // CITY.TELEMETRY</text>',
        f'  <text x="44" y="84" class="display" fill="#{theme["TEXT"]}" font-size="38">VISIBLE GITHUB ACTIVITY</text>',
        f'  <text x="44" y="114" class="ui" fill="#{theme["STEEL"]}" font-size="15">public contribution patterns, repo signals, and visible streak data tuned for cleaner GitHub readability.</text>',
        f'  <text x="952" y="50" text-anchor="end" class="mono" fill="#{theme["MUTED"]}" font-size="11">LIVE UPLINK</text>',
        f'  <rect x="-140" y="136" width="140" height="130" fill="url(#sweep)" opacity="0.34">',
        '    <animate attributeName="x" values="-140;1040;-140" dur="6.2s" repeatCount="indefinite" />',
        "  </rect>",
    ]

    for index, (x, (label, value, hint)) in enumerate(zip(tile_xs, tiles)):
        bar_width = 70 + (index * 12)
        svg.extend(
            [
                f'  <rect x="{x}" y="146" width="{tile_width}" height="96" rx="16" fill="#{theme["PANEL_ALT"]}" stroke="#{theme["EDGE"]}" stroke-opacity="0.55" />',
                f'  <rect x="{x}" y="146" width="{tile_width}" height="96" rx="16" fill="url(#tile-glow)" />',
                f'  <rect x="{x}" y="146" width="{tile_width}" height="96" rx="16" fill="url(#sweep)" opacity="0">',
                f'    <animate attributeName="opacity" values="0;0.18;0" dur="{4.2 + index * 0.5:.1f}s" repeatCount="indefinite" />',
                "  </rect>",
                f'  <rect x="{x + 18}" y="162" width="{bar_width}" height="3" rx="1.5" fill="#{theme["ACCENT"]}">',
                f'    <animate attributeName="width" values="{max(52, bar_width - 16)};{bar_width + 20};{bar_width}" dur="{3.8 + index * 0.4:.1f}s" repeatCount="indefinite" />',
                "  </rect>",
                f'  <circle cx="{x + tile_width - 26}" cy="166" r="4" fill="#{theme["ACCENT"]}">',
                f'    <animate attributeName="opacity" values="0.15;1;0.15" dur="{1.5 + index * 0.25:.1f}s" repeatCount="indefinite" />',
                "  </circle>",
                f'  <circle cx="{x + tile_width - 26}" cy="166" r="10" fill="none" stroke="#{theme["ACCENT"]}" stroke-opacity="0.2">',
                f'    <animate attributeName="r" values="7;14;7" dur="{1.5 + index * 0.25:.1f}s" repeatCount="indefinite" />',
                f'    <animate attributeName="stroke-opacity" values="0.2;0;0.2" dur="{1.5 + index * 0.25:.1f}s" repeatCount="indefinite" />',
                "  </circle>",
                f'  <text x="{x + 18}" y="204" class="display" fill="#{theme["TEXT"]}" font-size="44">{escape(str(value))}</text>',
                f'  <text x="{x + 18}" y="224" class="ui" fill="#{theme["ACCENT"]}" font-size="14">{escape(label.upper())}</text>',
                f'  <text x="{x + 18}" y="240" class="mono" fill="#{theme["MUTED"]}" font-size="11">{escape(hint)}</text>',
            ]
        )

    chip_gap = 12
    chip_widths = [136, 136, 136, 136]
    chip_x = (1000 - (sum(chip_widths) + chip_gap * (len(chip_widths) - 1))) / 2
    for chip, width in zip(chips, chip_widths):
        svg.extend(
            [
                f'  <rect x="{chip_x}" y="270" width="{width}" height="26" rx="13" fill="#{theme["PANEL_ALT"]}" stroke="#{theme["EDGE"]}" />',
                f'  <text x="{chip_x + width / 2}" y="287" text-anchor="middle" class="mono" fill="#{theme["STEEL"]}" font-size="11">{escape(chip)}</text>',
            ]
        )
        chip_x += width + chip_gap

    svg.append("</svg>")
    write_text_file(SCRIPT_DIR / "generated" / "activity.svg", "\n".join(svg))


def write_languages_svg(config, stats):
    theme = config["theme"]
    colors = [
        theme["ACCENT"],
        theme["ACCENT_2"],
        "74d3ae",
        "f28f79",
        "b997ff",
    ]
    rows = stats["languages"] or [{"name": "No public code yet", "percent": 100.0}]
    chips = [
        f"top {rows[0]['name']}" if rows else "top language n/a",
        f"repos {stats['public_repos']}",
        "public repos only",
    ]

    svg = [
        f'<svg viewBox="0 0 1000 332" xmlns="http://www.w3.org/2000/svg" width="1000" height="332" role="img" aria-label="Language mix for {escape(config["display_name"])}">',
        "  <defs>",
        '    <linearGradient id="panel-grad" x1="0" y1="0" x2="1" y2="1">',
        f'      <stop offset="0%" stop-color="#{theme["PANEL_SOFT"]}" />',
        f'      <stop offset="100%" stop-color="#{theme["PANEL"]}" />',
        "    </linearGradient>",
        '    <linearGradient id="bar-sweep" x1="0" y1="0" x2="1" y2="0">',
        f'      <stop offset="0%" stop-color="#{theme["TEXT"]}" stop-opacity="0" />',
        f'      <stop offset="50%" stop-color="#{theme["TEXT"]}" stop-opacity="0.24" />',
        f'      <stop offset="100%" stop-color="#{theme["TEXT"]}" stop-opacity="0" />',
        "    </linearGradient>",
        '    <clipPath id="mix-clip">',
        '      <rect x="44" y="138" width="912" height="24" rx="12" />',
        "    </clipPath>",
        '    <radialGradient id="marker-glow" cx="50%" cy="50%" r="50%">',
        f'      <stop offset="0%" stop-color="#{theme["ACCENT"]}" stop-opacity="0.9" />',
        f'      <stop offset="100%" stop-color="#{theme["ACCENT"]}" stop-opacity="0" />',
        "    </radialGradient>",
        *svg_style_block(),
        "  </defs>",
        f'  <rect width="1000" height="332" fill="#{theme["BG"]}" />',
        f'  <rect x="24" y="18" width="952" height="296" rx="20" fill="url(#panel-grad)" stroke="#{theme["EDGE"]}" stroke-opacity="0.6" />',
        f'  <text x="44" y="50" class="mono" fill="#{theme["ACCENT"]}" font-size="12">LANGUAGE.ANALYSIS</text>',
        f'  <text x="44" y="84" class="display" fill="#{theme["TEXT"]}" font-size="38">PUBLIC REPO LANGUAGE SPREAD</text>',
        f'  <text x="44" y="114" class="ui" fill="#{theme["STEEL"]}" font-size="15">weighted by owned public repos, with larger labels and darker telemetry spacing for GitHub profile view.</text>',
        f'  <text x="952" y="50" text-anchor="end" class="mono" fill="#{theme["MUTED"]}" font-size="11">OWNED PUBLIC REPOS</text>',
        f'  <rect x="44" y="138" width="912" height="24" rx="12" fill="#{theme["PANEL_ALT"]}" />',
    ]

    current_x = 44
    remaining_width = 912
    for index, row in enumerate(rows):
        width = remaining_width if index == len(rows) - 1 else round(912 * (row["percent"] / 100.0))
        remaining_width -= width
        color = colors[index % len(colors)]
        svg.append(
            f'  <rect x="{current_x}" y="138" width="{max(width, 0)}" height="24" rx="12" fill="#{color}" />'
        )
        current_x += width

    svg.extend(
        [
            '  <g clip-path="url(#mix-clip)">',
            '    <rect x="-120" y="138" width="120" height="24" fill="url(#bar-sweep)" opacity="0.42">',
            '      <animate attributeName="x" values="-120;1020;-120" dur="4.8s" repeatCount="indefinite" />',
            "    </rect>",
            f'    <circle cx="44" cy="150" r="9" fill="url(#marker-glow)" opacity="0.58">',
            '      <animate attributeName="cx" values="44;956;44" dur="6.2s" repeatCount="indefinite" />',
            '    </circle>',
            "  </g>",
        ]
    )

    start_y = 196
    for index, row in enumerate(rows[:5]):
        color = colors[index % len(colors)]
        y = start_y + index * 28
        svg.extend(
            [
                f'  <circle cx="54" cy="{y - 5}" r="6" fill="#{color}">',
                f'    <animate attributeName="opacity" values="0.4;1;0.4" dur="{2.2 + index * 0.3:.1f}s" repeatCount="indefinite" />',
                "  </circle>",
                f'  <text x="74" y="{y}" class="ui" fill="#{theme["TEXT"]}" font-size="20">{escape(row["name"])}</text>',
                f'  <text x="948" y="{y}" text-anchor="end" class="mono" fill="#{theme["STEEL"]}" font-size="16">{row["percent"]:.1f}%</text>',
            ]
        )

    note = "public orgs hidden or none" if stats["public_orgs"] == 0 else f"public orgs {stats['public_orgs']}"
    svg.append(
        f'  <text x="948" y="114" text-anchor="end" class="mono" fill="#{theme["MUTED"]}" font-size="12">{escape(note)}</text>'
    )

    chip_gap = 12
    chip_widths = [max(140, min(192, len(item) * 7 + 28)) for item in chips]
    chip_total = sum(chip_widths) + chip_gap * max(0, len(chip_widths) - 1)
    chip_x = (1000 - chip_total) / 2
    for item, width in zip(chips, chip_widths):
        svg.extend(
            [
                f'  <rect x="{chip_x}" y="276" width="{width}" height="26" rx="13" fill="#{theme["PANEL_ALT"]}" stroke="#{theme["EDGE"]}" />',
                f'  <text x="{chip_x + width / 2}" y="293" text-anchor="middle" class="mono" fill="#{theme["STEEL"]}" font-size="11">{escape(item)}</text>',
            ]
        )
        chip_x += width + chip_gap

    svg.append("</svg>")
    write_text_file(SCRIPT_DIR / "generated" / "languages.svg", "\n".join(svg))


def write_orgs_svg(config, orgs):
    theme = config["theme"]
    display_orgs = orgs[:2]
    if not display_orgs:
        display_orgs = [
            {
                "label": "No public org spotlight yet",
                "headline": "Add an organization in config to feature team work here.",
                "website": "",
                "location": "",
                "public_repos": 0,
                "followers": 0,
                "public_membership": False,
                "top_repo_name": "",
                "top_repo_desc": "",
                "top_repo_stars": 0,
            }
        ]

    card_gap = 18
    card_width = 912 if len(display_orgs) == 1 else 447
    positions = [44 + index * (card_width + card_gap) for index in range(len(display_orgs))]

    svg = [
        f'<svg viewBox="0 0 1000 332" xmlns="http://www.w3.org/2000/svg" width="1000" height="332" role="img" aria-label="Organization spotlight for {escape(config["display_name"])}">',
        "  <defs>",
        '    <linearGradient id="panel-grad" x1="0" y1="0" x2="1" y2="1">',
        f'      <stop offset="0%" stop-color="#{theme["PANEL_SOFT"]}" />',
        f'      <stop offset="100%" stop-color="#{theme["PANEL"]}" />',
        "    </linearGradient>",
        '    <linearGradient id="card-sweep" x1="0" y1="0" x2="1" y2="0">',
        f'      <stop offset="0%" stop-color="#{theme["ACCENT"]}" stop-opacity="0" />',
        f'      <stop offset="50%" stop-color="#{theme["ACCENT"]}" stop-opacity="0.32" />',
        f'      <stop offset="100%" stop-color="#{theme["ACCENT"]}" stop-opacity="0" />',
        "    </linearGradient>",
        *svg_style_block(),
        "  </defs>",
        f'  <rect width="1000" height="332" fill="#{theme["BG"]}" />',
        f'  <rect x="24" y="18" width="952" height="296" rx="20" fill="url(#panel-grad)" stroke="#{theme["EDGE"]}" stroke-opacity="0.6" />',
        f'  <text x="44" y="50" class="mono" fill="#{theme["ACCENT"]}" font-size="12">ORG.SPOTLIGHT</text>',
        f'  <text x="44" y="84" class="display" fill="#{theme["TEXT"]}" font-size="38">WORK BEYOND PERSONAL REPOS</text>',
        f'  <text x="44" y="114" class="ui" fill="#{theme["STEEL"]}" font-size="15">organization contributions, public membership signals, and team context rendered with wider spacing and cleaner type.</text>',
    ]

    for index, (x, org) in enumerate(zip(positions, display_orgs)):
        beacon_color = theme["ACCENT"] if org.get("public_membership") else theme["ACCENT_2"]
        member_text = "membership public" if org.get("public_membership") else "membership hidden"
        top_repo_name = org.get("top_repo_name") or "repo signal unavailable"
        top_repo_desc = org.get("top_repo_desc") or "public repo details not exposed here yet"
        headline_lines = split_text(org["headline"], 34 if card_width > 500 else 26, 2)
        desc_lines = split_text(top_repo_desc, 48 if card_width > 500 else 28, 2)

        svg.extend(
            [
                f'  <rect x="{x}" y="138" width="{card_width}" height="130" rx="18" fill="#{theme["PANEL_ALT"]}" stroke="#{theme["EDGE"]}" />',
                f'  <rect x="{x - 120}" y="138" width="120" height="130" fill="url(#card-sweep)" opacity="0.26">',
                f'    <animate attributeName="x" values="{x - 120};{x + card_width};{x - 120}" dur="{6.2 + index * 0.6:.1f}s" repeatCount="indefinite" />',
                "  </rect>",
                f'  <text x="{x + 18}" y="166" class="display" fill="#{theme["TEXT"]}" font-size="30">{escape(org["label"])}</text>',
                f'  <text x="{x + 18}" y="190" class="ui" fill="#{theme["STEEL"]}" font-size="14">{escape(headline_lines[0])}</text>',
                f'  <text x="{x + 18}" y="210" class="ui" fill="#{theme["STEEL"]}" font-size="14">{escape(headline_lines[1])}</text>',
                f'  <circle cx="{x + card_width - 22}" cy="154" r="5" fill="#{beacon_color}">',
                f'    <animate attributeName="opacity" values="0.24;1;0.24" dur="{1.9 + index * 0.4:.1f}s" repeatCount="indefinite" />',
                "  </circle>",
                f'  <text x="{x + card_width - 36}" y="158" text-anchor="end" class="mono" fill="#{theme["MUTED"]}" font-size="11">{escape(member_text)}</text>',
                f'  <text x="{x + 18}" y="236" class="mono" fill="#{theme["ACCENT"]}" font-size="12">top repo: {escape(top_repo_name)}</text>',
                f'  <text x="{x + 18}" y="254" class="ui" fill="#{theme["MUTED"]}" font-size="13">{escape(desc_lines[0])}</text>',
                f'  <text x="{x + 18}" y="272" class="ui" fill="#{theme["MUTED"]}" font-size="13">{escape(desc_lines[1])}</text>',
            ]
        )

        chips = [
            f'repos {org["public_repos"]}',
            f'followers {org["followers"]}',
            f'location {org["location"] or "n/a"}',
        ]
        if org.get("top_repo_stars"):
            chips.append(f'stars {org["top_repo_stars"]}')
        if org.get("website"):
            chips.append(org["website"].replace("https://", ""))

        chip_widths = [max(102, min(184, len(item) * 7 + 24)) for item in chips[:4]]
        chip_total = sum(chip_widths) + 8 * max(0, len(chip_widths) - 1)
        chip_x = x + max(18, (card_width - chip_total) / 2)
        chip_y = 284
        for item, width in zip(chips[:4], chip_widths):
            svg.extend(
                [
                    f'  <rect x="{chip_x}" y="{chip_y}" width="{width}" height="24" rx="12" fill="#{theme["PANEL"]}" stroke="#{theme["EDGE"]}" />',
                    f'  <text x="{chip_x + width / 2}" y="{chip_y + 16}" text-anchor="middle" class="mono" fill="#{theme["STEEL"]}" font-size="11">{escape(item)}</text>',
                ]
            )
            chip_x += width + 8

    svg.append("</svg>")
    write_text_file(SCRIPT_DIR / "generated" / "orgs.svg", "\n".join(svg))


def main():
    config = load_config()
    try:
        stats = fetch_public_stats(config["username"])
        org_spotlights = fetch_org_spotlights(config)
    except Exception as exc:
        print(f"warning: failed to fetch GitHub data: {exc}")
        stats = empty_stats()
        org_spotlights = []

    context = build_context(config, stats)

    for template_name, output_name in config["templates"].items():
        render_template(
            TEMPLATES_DIR / template_name,
            SCRIPT_DIR / output_name,
            context,
        )

    write_activity_svg(config, stats)
    write_languages_svg(config, stats)
    write_orgs_svg(config, org_spotlights)


if __name__ == "__main__":
    main()
