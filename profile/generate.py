#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config" / "config.json"
TEMPLATES_DIR = SCRIPT_DIR / "templates"


def load_config():
    return json.loads(CONFIG_PATH.read_text())


def build_context(config):
    context = {
        "USERNAME": config["username"],
        "DISPLAY_NAME": config["display_name"],
        "TAGLINE": config["tagline"],
        "YEAR": str(datetime.now().year),
    }
    context.update(config["theme"])

    for key in ("mission", "toolbelt", "focus", "tags"):
        values = config[key]
        for index, value in enumerate(values, start=1):
            context[f"{key.upper()}_{index}"] = value

    theme = config["theme"]
    username = config["username"]
    repo = config["repo"]

    stats_params = {
        "username": username,
        "show_icons": "true",
        "include_all_commits": "true",
        "count_private": "true",
        "hide_border": "true",
        "bg_color": theme["PANEL"],
        "title_color": theme["ACCENT"],
        "text_color": theme["TEXT"],
        "icon_color": theme["ACCENT"],
        "border_radius": "0",
    }
    langs_params = {
        "username": username,
        "layout": "compact",
        "langs_count": "8",
        "hide": "html,css,jupyter notebook",
        "hide_border": "true",
        "bg_color": theme["PANEL"],
        "title_color": theme["ACCENT"],
        "text_color": theme["TEXT"],
        "border_radius": "0",
    }
    streak_params = {
        "user": username,
        "hide_border": "true",
        "background": theme["PANEL"],
        "ring": theme["ACCENT"],
        "fire": theme["ACCENT"],
        "currStreakLabel": theme["ACCENT"],
        "currStreakNum": theme["TEXT"],
        "sideNums": theme["TEXT"],
        "sideLabels": theme["TEXT"],
        "dates": theme["MUTED"],
        "stroke": theme["EDGE"],
        "border_radius": "0",
        "mode": "weekly",
        "date_format": "j M[ Y]",
    }

    context["README_STATS_URL"] = (
        "https://github-readme-stats.vercel.app/api?" + urlencode(stats_params)
    )
    context["README_LANGS_URL"] = (
        "https://github-readme-stats.vercel.app/api/top-langs?" + urlencode(langs_params)
    )
    context["README_STREAK_URL"] = (
        "https://streak-stats.demolab.com/?" + urlencode(streak_params)
    )
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


def main():
    config = load_config()
    context = build_context(config)

    for template_name, output_name in config["templates"].items():
        render_template(
            TEMPLATES_DIR / template_name,
            SCRIPT_DIR / output_name,
            context,
        )


if __name__ == "__main__":
    main()
