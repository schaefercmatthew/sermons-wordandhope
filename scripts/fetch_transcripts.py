#!/usr/bin/env python3
"""
Checks the SermonAudio RSS feed for sermons that don't have a transcript
file saved yet, and for each one, fetches its transcript (if SermonAudio
has one on file) and commits it as a plain .txt file to the /transcripts
folder on the main branch.

This script does the fetching only. It does not write articles, does not
call any AI service, and does not touch articles-data.json or index.html.
Turning a transcript into a finished, published article is done entirely
by a separate, daily Plaud scheduled task — see PLAUD_AGENT_INSTRUCTIONS.md
for exactly what that task does.

A sermon is considered "already handled" once a matching /transcripts/
{slug}.txt file exists in the repo — this script never revisits a slug it
has already written, whether or not an article has been written from it
yet.

On the very first run (when /transcripts is empty), there will usually be
many sermons to fetch at once. Rather than writing dozens of files in one
run, this script writes the oldest MAX_TRANSCRIPTS_PER_RUN of them and
says so in its log output — running the workflow again (by hand, or on
its next scheduled run) works through the rest a few at a time.

You should not need to edit this file. If SermonAudio changes the format
of their feed or their API, the "Parse the feed" or "Fetch the transcript"
sections below are the parts that would need updating — see the setup
guide's troubleshooting section.
"""

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

FEED_URL = "https://feed.sermonaudio.com/speaker/65786"
SERMONAUDIO_API_BASE = "https://api.sermonaudio.com/v2"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSCRIPTS_DIR = os.path.join(REPO_ROOT, "transcripts")

MAX_TRANSCRIPTS_PER_RUN = 5


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[:.]", "-", slug)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]


def extract_sermon_id(link: str, guid: str) -> str:
    """Pulls the numeric SermonAudio sermon ID out of a feed item's link or guid.

    SermonAudio sermon URLs look like:
      https://www.sermonaudio.com/sermons/81626155257918
    The trailing digits are the sermon_id the SermonAudio API expects.
    """
    for candidate in (link, guid):
        if not candidate:
            continue
        match = re.search(r"/sermons/(\d+)", candidate)
        if match:
            return match.group(1)
    return ""


def fetch_feed() -> list[dict]:
    """Downloads and parses the RSS feed into a list of sermon dicts."""
    response = requests.get(FEED_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    root = ET.fromstring(response.content)

    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
    sermons = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        subtitle = (item.findtext("itunes:subtitle", namespaces=ns) or "").strip()

        series = ""
        if " - " in subtitle:
            series = subtitle.split(" - ", 1)[1].strip()

        pub_date_raw = (item.findtext("pubDate") or "").strip()
        pub_date_display = pub_date_raw
        pub_date_iso = ""
        if pub_date_raw:
            try:
                dt = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %z")
                pub_date_display = dt.strftime("%B %-d, %Y")
                pub_date_iso = dt.date().isoformat()
            except ValueError:
                pass

        if not title or not guid:
            continue

        sermons.append(
            {
                "guid": guid,
                "title": title,
                "sermonaudio_url": link,
                "sermon_id": extract_sermon_id(link, guid),
                "series": series,
                "date_display": pub_date_display,
                "date_iso": pub_date_iso,
            }
        )
    return sermons


def fetch_transcript(sermon_id: str) -> dict:
    """Looks up a sermon on the SermonAudio API and returns its transcript, if any.

    Returns a dict: {"available": bool, "text": str, "note": str}.
    Many sermons on SermonAudio simply have no transcript on file — that is
    normal, not an error, and is handled here rather than treated as a
    failure.
    """
    api_key = os.environ.get("SERMONAUDIO_API_KEY", "")
    if not api_key:
        return {
            "available": False,
            "text": "",
            "note": "No SERMONAUDIO_API_KEY was configured, so the transcript lookup was skipped.",
        }
    if not sermon_id:
        return {
            "available": False,
            "text": "",
            "note": "Could not determine this sermon's SermonAudio ID from the feed, so the transcript lookup was skipped.",
        }

    headers = {"x-api-key": api_key}
    detail_url = f"{SERMONAUDIO_API_BASE}/node/sermons/{sermon_id}"
    response = requests.get(detail_url, headers=headers, timeout=30)
    if response.status_code != 200:
        return {
            "available": False,
            "text": "",
            "note": f"SermonAudio API returned an error looking up this sermon (status {response.status_code}).",
        }

    sermon_record = response.json()
    transcript_info = sermon_record.get("transcript")
    if not transcript_info or not transcript_info.get("downloadURL"):
        return {
            "available": False,
            "text": "",
            "note": "SermonAudio does not have a transcript on file for this sermon.",
        }

    transcript_response = requests.get(transcript_info["downloadURL"], timeout=30)
    if transcript_response.status_code != 200:
        return {
            "available": False,
            "text": "",
            "note": "SermonAudio listed a transcript for this sermon, but it could not be downloaded.",
        }

    return {"available": True, "text": transcript_response.text.strip(), "note": ""}


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=True, **kwargs)


def existing_transcript_slugs() -> set[str]:
    if not os.path.isdir(TRANSCRIPTS_DIR):
        return set()
    return {
        os.path.splitext(name)[0]
        for name in os.listdir(TRANSCRIPTS_DIR)
        if name.endswith(".txt")
    }


def write_transcript_file(sermon: dict, existing_slugs: set[str], claimed_slugs: set[str]) -> str:
    """Writes one sermon's transcript file into /transcripts and returns its slug."""
    base_slug = slugify(sermon["title"])
    taken = existing_slugs | claimed_slugs
    slug = base_slug
    if slug in taken and sermon.get("date_iso"):
        slug = f"{base_slug}-{sermon['date_iso']}"
    suffix = 2
    while slug in taken:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    transcript = fetch_transcript(sermon["sermon_id"])

    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{slug}.txt")

    header_lines = [
        f"SERMON_TITLE: {sermon['title']}",
        f"SERIES: {sermon['series'] or 'Not specified'}",
        f"DATE_PREACHED: {sermon['date_display']}",
        f"SERMONAUDIO_URL: {sermon['sermonaudio_url']}",
        f"SLUG: {slug}",
        f"DATE_ISO: {sermon['date_iso']}",
        f"GUID: {sermon['guid']}",
        "---",
        "",
    ]
    if transcript["available"]:
        body_text = transcript["text"]
    else:
        body_text = (
            f"(No transcript available from SermonAudio: {transcript['note']}\n"
            "Write the article from the sermon title, scripture, and series above, "
            "grounded in the passage itself — do not invent quotes or claims about "
            "what was specifically said.)"
        )

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write("\n".join(header_lines) + body_text)

    run(["git", "add", transcript_path])
    return slug


def main() -> None:
    print(f"Fetching feed: {FEED_URL}")
    sermons = fetch_feed()
    print(f"Feed returned {len(sermons)} sermon(s).")

    if not sermons:
        print(
            "The feed came back empty. This usually means SermonAudio's feed is "
            "temporarily unreachable or its format changed — nothing was skipped, "
            "there was simply nothing to read. Try running this workflow again by hand "
            "in a few minutes; if it keeps happening, see the setup guide's "
            "troubleshooting section."
        )
        return

    existing_slugs = existing_transcript_slugs()
    is_first_run = len(existing_slugs) == 0
    # A sermon is "new" if no transcript file already exists for its slug.
    # We compute each sermon's slug the same way write_transcript_file does,
    # but do it here first just to filter the list before doing any work.
    new_sermons = []
    for sermon in sermons:
        base_slug = slugify(sermon["title"])
        candidates = {base_slug, f"{base_slug}-{sermon.get('date_iso', '')}"}
        if existing_slugs & candidates:
            continue
        new_sermons.append(sermon)

    if not new_sermons:
        print("No new sermons found — every sermon in the feed already has a transcript file. Nothing to do.")
        return

    if is_first_run and len(new_sermons) > MAX_TRANSCRIPTS_PER_RUN:
        print(
            f"This looks like a first run: the /transcripts folder is empty, but the "
            f"feed has {len(new_sermons)} sermon(s). Rather than writing "
            f"{len(new_sermons)} transcript files at once, this run will write the "
            f"{MAX_TRANSCRIPTS_PER_RUN} oldest ones first, so the Plaud scheduled task has a "
            "manageable batch to work through. Run this workflow again (or wait for "
            "tomorrow's scheduled run) to work through the rest a few at a time."
        )
        new_sermons = sorted(new_sermons, key=lambda s: s.get("date_iso", ""))[:MAX_TRANSCRIPTS_PER_RUN]

    run(["git", "config", "user.name", "sermon-transcript-bot"])
    run(["git", "config", "user.email", "actions@users.noreply.github.com"])

    print(f"Fetching transcripts for {len(new_sermons)} sermon(s)...")
    written = 0
    claimed_slugs: set[str] = set()
    written_titles: list[str] = []
    for sermon in new_sermons:
        try:
            print(f"Fetching transcript for: {sermon['title']}")
            slug = write_transcript_file(sermon, existing_slugs, claimed_slugs)
            claimed_slugs.add(slug)
            written_titles.append(f"{sermon['title']} -> transcripts/{slug}.txt")
            written += 1
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to fetch transcript for '{sermon['title']}': {exc}", file=sys.stderr)
            continue

    if written == 0:
        print("No transcript files were written this run.")
        return

    commit_message = "Fetch sermon transcript(s): " + "; ".join(
        sermon["title"] for sermon in new_sermons[:written]
    )
    run(["git", "commit", "-m", commit_message])
    run(["git", "push"])

    print(f"Done. Committed {written} transcript file(s) to /transcripts on main:")
    for line in written_titles:
        print(f"  - {line}")


if __name__ == "__main__":
    main()
