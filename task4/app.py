import csv
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CANVAS_URL = os.getenv("CANVAS_URL", "").rstrip("/")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN", "")
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "14"))
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/data/output"))
LOCAL_TZ = ZoneInfo(os.getenv("TZ_NAME", "Australia/Melbourne"))

session = requests.Session()
session.headers["Authorization"] = f"Bearer {CANVAS_TOKEN}"


def get_all(path, params=None):
    """GET a Canvas API endpoint and follow pagination links."""
    url, results = f"{CANVAS_URL}/api/v1/{path}", []
    while url:
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results.extend(resp.json())
        # The next-page URL already contains the query string
        url, params = resp.links.get("next", {}).get("url"), None
    return results


def collect_deadlines():
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=DAYS_AHEAD)
    deadlines = []

    courses = get_all("courses", {"enrollment_state": "active", "per_page": 100})
    logging.info("Found %d active course(s)", len(courses))

    for course in courses:
        code = course.get("course_code") or course.get("name") or f"Course {course['id']}"
        try:
            assignments = get_all(f"courses/{course['id']}/assignments",
                                  {"bucket": "future", "include[]": "submission", "per_page": 100})
        except requests.HTTPError as e:
            # Some courses restrict API access; skip them instead of failing the whole run
            logging.warning("Skipping %s: %s", code, e)
            continue

        for a in assignments:
            if not a.get("due_at"):
                continue
            due = datetime.fromisoformat(a["due_at"].replace("Z", "+00:00"))
            submitted = bool((a.get("submission") or {}).get("submitted_at"))
            if now <= due <= cutoff and not submitted:
                deadlines.append({
                    "course": code,
                    "assignment": a["name"],
                    "due_local": due.astimezone(LOCAL_TZ).strftime("%a %d %b %H:%M"),
                    "days_left": (due - now).days,
                    "url": a.get("html_url", ""),
                    "_due": due,
                })
        logging.info("%s: checked %d future assignment(s)", code, len(assignments))

    return sorted(deadlines, key=lambda d: d["_due"])


def write_report(deadlines):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"deadlines_{datetime.now(LOCAL_TZ):%Y%m%d_%H%M%S}.csv"
    fields = ["course", "assignment", "due_local", "days_left", "url"]
    # utf-8-sig lets Excel open the file with the correct encoding
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(deadlines)
    logging.info("Report saved to %s", path)


def notify_discord(deadlines):
    if not DISCORD_WEBHOOK_URL:
        logging.info("DISCORD_WEBHOOK_URL not set; skipping Discord notification")
        return
    lines = [f"**Upcoming deadlines (next {DAYS_AHEAD} days)**"]
    lines += [f"- {d['course']}: {d['assignment']} - {d['due_local']} ({d['days_left']}d left)"
              for d in deadlines] or ["Nothing due. Nice!"]

    resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": "\n".join(lines)[:2000]}, timeout=15)
    resp.raise_for_status()
    logging.info("Discord notification sent")


def main():
    if not CANVAS_URL or not CANVAS_TOKEN:
        logging.error("CANVAS_URL and CANVAS_TOKEN must be set")
        sys.exit(1)

    logging.info("Checking Canvas for deadlines in the next %d days", DAYS_AHEAD)
    try:
        deadlines = collect_deadlines()
    except requests.HTTPError as e:
        logging.error("Canvas API request failed: %s", e)
        sys.exit(1)

    for d in deadlines:
        logging.info("DUE %s | %s | %s", d["due_local"], d["course"], d["assignment"])

    write_report(deadlines)
    notify_discord(deadlines)
    logging.info("Done: %d unsubmitted assignment(s) due soon", len(deadlines))


if __name__ == "__main__":
    main()