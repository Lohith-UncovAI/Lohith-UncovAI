#!/usr/bin/env python3
import json
import os
import re
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from urllib.parse import urlencode
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
        language_rows.append(
            {
                "name": language,
                "percent": percent,
            }
        )

    return {
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": len(public_repos),
        "public_orgs": len(orgs),
        "total_stars": total_stars,
        "languages": language_rows,
        **activity,
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

    for key in ("mission", "toolbelt", "focus", "tags"):
        values = config[key]
        for index, value in enumerate(values, start=1):
            context[f"{key.upper()}_{index}"] = value

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
    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", value)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(content)
    print(f"generated {destination_path.relative_to(SCRIPT_DIR.parent)}")


def write_text_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"generated {path.relative_to(SCRIPT_DIR.parent)}")


def write_activity_svg(config, stats):
    theme = config["theme"]
    tiles = [
        ("Public Contributions", stats["total_contributions"], "last 12 months"),
        ("Active Days", stats["active_days"], "days with visible activity"),
        ("Current Streak", stats["current_streak"], "consecutive active days"),
        ("Best Streak", stats["best_streak"], "longest run so far"),
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
        '<svg viewBox="0 0 1000 254" xmlns="http://www.w3.org/2000/svg" width="1000" height="254" role="img" aria-label="Public activity summary for lohith">',
        "  <defs>",
        "    <style>",
        '      .mono { font-family: "SFMono-Regular", "Consolas", "Liberation Mono", monospace; }',
        '      .ui { font-family: "Trebuchet MS", "Verdana", sans-serif; }',
        "    </style>",
        "  </defs>",
        f'  <rect width="1000" height="254" fill="#{theme["BG"]}" />',
        f'  <rect x="24" y="20" width="952" height="210" rx="16" fill="#{theme["PANEL"]}" stroke="#{theme["EDGE"]}" />',
        f'  <text x="44" y="50" class="mono" fill="#{theme["ACCENT"]}" font-size="14">public.signal</text>',
        f'  <text x="44" y="78" class="ui" fill="#{theme["TEXT"]}" font-size="28" font-weight="700">visible GitHub activity</text>',
        f'  <text x="44" y="100" class="ui" fill="#{theme["MUTED"]}" font-size="15">public profile data only. org or private work appears here only when GitHub exposes it publicly.</text>',
    ]

    for x, (label, value, hint) in zip(tile_xs, tiles):
        svg.extend(
            [
                f'  <rect x="{x}" y="122" width="{tile_width}" height="76" rx="12" fill="#{theme["PANEL_ALT"]}" stroke="#{theme["EDGE"]}" />',
                f'  <text x="{x + 18}" y="152" class="ui" fill="#{theme["TEXT"]}" font-size="30" font-weight="700">{escape(str(value))}</text>',
                f'  <text x="{x + 18}" y="174" class="ui" fill="#{theme["ACCENT"]}" font-size="15">{escape(label)}</text>',
                f'  <text x="{x + 18}" y="191" class="mono" fill="#{theme["MUTED"]}" font-size="11">{escape(hint)}</text>',
            ]
        )

    chip_x = 44
    for chip in chips:
        width = max(108, len(chip) * 7 + 24)
        svg.extend(
            [
                f'  <rect x="{chip_x}" y="212" width="{width}" height="24" rx="12" fill="#{theme["PANEL_ALT"]}" stroke="#{theme["EDGE"]}" />',
                f'  <text x="{chip_x + width / 2}" y="228" text-anchor="middle" class="mono" fill="#{theme["STEEL"]}" font-size="12">{escape(chip)}</text>',
            ]
        )
        chip_x += width + 10

    svg.append("</svg>")
    write_text_file(SCRIPT_DIR / "generated" / "activity.svg", "\n".join(svg))


def write_languages_svg(config, stats):
    theme = config["theme"]
    colors = ["f4d35e", "86a8ff", "5dd39e", "f28482", "cdb4db"]
    rows = stats["languages"] or [{"name": "No public code yet", "percent": 100.0}]

    svg = [
        '<svg viewBox="0 0 1000 228" xmlns="http://www.w3.org/2000/svg" width="1000" height="228" role="img" aria-label="Language mix for lohith">',
        "  <defs>",
        "    <style>",
        '      .mono { font-family: "SFMono-Regular", "Consolas", "Liberation Mono", monospace; }',
        '      .ui { font-family: "Trebuchet MS", "Verdana", sans-serif; }',
        "    </style>",
        "  </defs>",
        f'  <rect width="1000" height="228" fill="#{theme["BG"]}" />',
        f'  <rect x="24" y="18" width="952" height="192" rx="16" fill="#{theme["PANEL"]}" stroke="#{theme["EDGE"]}" />',
        f'  <text x="44" y="48" class="mono" fill="#{theme["ACCENT"]}" font-size="14">language.mix</text>',
        f'  <text x="44" y="76" class="ui" fill="#{theme["TEXT"]}" font-size="28" font-weight="700">public repo language spread</text>',
        f'  <text x="44" y="98" class="ui" fill="#{theme["MUTED"]}" font-size="15">aggregated from owned public repositories</text>',
        f'  <rect x="44" y="118" width="912" height="18" rx="9" fill="#{theme["PANEL_ALT"]}" />',
    ]

    current_x = 44
    total_width = 912
    for index, row in enumerate(rows):
        width = total_width if index == len(rows) - 1 else round(total_width * (row["percent"] / 100.0))
        total_width -= width
        color = colors[index % len(colors)]
        svg.append(
            f'  <rect x="{current_x}" y="118" width="{max(width, 0)}" height="18" rx="9" fill="#{color}" />'
        )
        current_x += width

    start_y = 164
    for index, row in enumerate(rows[:5]):
        color = colors[index % len(colors)]
        y = start_y + index * 22
        svg.extend(
            [
                f'  <circle cx="52" cy="{y - 5}" r="6" fill="#{color}" />',
                f'  <text x="68" y="{y}" class="ui" fill="#{theme["TEXT"]}" font-size="18">{escape(row["name"])}</text>',
                f'  <text x="948" y="{y}" text-anchor="end" class="mono" fill="#{theme["STEEL"]}" font-size="15">{row["percent"]:.1f}%</text>',
            ]
        )

    if stats["public_orgs"] == 0:
        note = "public orgs: hidden or none"
    else:
        note = f"public orgs: {stats['public_orgs']}"
    svg.append(
        f'  <text x="948" y="98" text-anchor="end" class="mono" fill="#{theme["MUTED"]}" font-size="12">{escape(note)}</text>'
    )
    svg.append("</svg>")
    write_text_file(SCRIPT_DIR / "generated" / "languages.svg", "\n".join(svg))


def main():
    config = load_config()
    try:
        stats = fetch_public_stats(config["username"])
    except Exception as exc:
        print(f"warning: failed to fetch GitHub data: {exc}")
        stats = {
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

    context = build_context(config, stats)

    for template_name, output_name in config["templates"].items():
        render_template(
            TEMPLATES_DIR / template_name,
            SCRIPT_DIR / output_name,
            context,
        )

    write_activity_svg(config, stats)
    write_languages_svg(config, stats)


if __name__ == "__main__":
    main()
