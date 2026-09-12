#!/usr/bin/env python3
"""
Checks the SermonAudio RSS feed for sermons that don't have an article yet
on sermons.wordandhope.com, drafts an article for each one using Claude,
and opens a separate pull request per sermon for human review.

You should not need to edit this file. If SermonAudio changes the format
of their feed, the "Parse the feed" section below is the part that would
need updating — see the setup guide's troubleshooting section.
"""

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests
from anthropic import Anthropic

FEED_URL = "https://feed.sermonaudio.com/speaker/65786"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(REPO_ROOT, "articles-data.json")
TEMPLATE_FILE = os.path.join(REPO_ROOT, "article-template.html")
INDEX_TEMPLATE_FILE = os.path.join(REPO_ROOT, "scripts", "articles_index_template.html")
INDEX_FILE = os.path.join(REPO_ROOT, "index.html")

CHURCH_NAME = "First Baptist Church of Wellston"
PASTOR_NAME = "Matthew Schaefer"
SITE_NAME = "Word and Hope"


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[:.]", "-", slug)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]


def fetch_feed() -> list[dict]:
    """Downloads and parses the RSS feed into a list of sermon dicts.

    Only assumes the standard RSS/iTunes-podcast fields that SermonAudio's
    feed has used historically: title, link, guid, enclosure (audio url),
    pubDate, and optionally description and itunes:subtitle (which
    SermonAudio uses for "Speaker - Series").
    """
    response = requests.get(FEED_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    root = ET.fromstring(response.content)

    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
    sermons = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        description = (item.findtext("description") or "").strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        subtitle = (item.findtext("itunes:subtitle", namespaces=ns) or "").strip()

        series = ""
        if " - " in subtitle:
            series = subtitle.split(" - ", 1)[1].strip()

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
                "description": description,
                "series": series,
                "date_display": pub_date_display,
                "date_iso": pub_date_iso,
            }
        )
    return sermons


def load_articles_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"articles": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_articles_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def rebuild_index(data: dict) -> None:
    with open(INDEX_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        index_template = f.read()

    items_html = []
    articles_sorted = sorted(data["articles"], key=lambda a: a.get("date_iso", ""), reverse=True)
    for article in articles_sorted:
        items_html.append(
            f"""  <li>
    <a class="title" href="/{article['slug']}.html">{article['title']}</a>
    <span class="meta">{article['scripture']} &middot; {article['date_display']}</span>
  </li>"""
        )
    list_html = "\n".join(items_html) if items_html else '  <li class="empty-note">No articles yet.</li>'

    output = index_template.replace("{{ARTICLE_LIST_ITEMS}}", list_html)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(output)


def build_prompt(sermon: dict, template_html: str, example_article_html: str) -> str:
    has_description = bool(sermon["description"].strip())

    source_material = (
        f'The sermon includes this description written by the pastor:\n"""\n{sermon["description"]}\n"""\n'
        if has_description
        else (
            "No written description or transcript is available for this sermon — only its title, "
            "scripture reference, and series are known. Write an original article grounded in the "
            "referenced Bible passage itself (as a faithful, conservative Baptist pastor would preach "
            "it), rather than guessing at what was specifically said in this particular sermon. Do not "
            "invent quotes, anecdotes, or claims about what was said in the sermon that you cannot know."
        )
    )

    return f"""You are drafting a written article for a pastor's church website, based on one of his sermons. \
Match the tone, structure, and theological voice of the EXAMPLE ARTICLE below exactly — warm, direct, \
pastoral, conservative evangelical Baptist theology, first-person illustrations used sparingly and only \
when clearly general (never inventing specific personal anecdotes that aren't given to you), heavy and \
accurate use of Scripture quoted from the ESV, section headings via <h2>/<h3>, and a closing structure \
that matches the example (a "soil-list"-style application section is optional and only appropriate if the \
passage lends itself to a parallel list structure — do not force it).

EXAMPLE ARTICLE (match this style and structure, written for the same site, same author):
---
{example_article_html}
---

Now write a NEW article for this sermon:
- Sermon title: {sermon['title']}
- Scripture reference: {sermon['title']}
- Series: {sermon['series'] or 'Not specified'}
- Date preached: {sermon['date_display']}
{source_material}

Output ONLY a JSON object (no markdown fences, no commentary) with exactly these keys:
{{
  "article_title": "an SEO-friendly, human-sounding title, e.g. 'What Does the Bible Say About X?' style if it fits, otherwise a natural title",
  "article_description": "one or two sentence meta description, under 200 characters",
  "kicker": "short category label, e.g. 'Bible Topics · The Psalms'",
  "deck": "one or two sentence subtitle/summary shown under the title",
  "hero_image_alt": "a plain description of a fitting stock-photo style hero image",
  "hero_caption": "a short italic caption, often a quoted verse fragment with reference",
  "article_body_html": "the full article body as HTML, using <section><h2>...</h2><p>...</p></section> blocks, blockquote.verse for Scripture quotes with <cite>, and optionally .pull for a pull-quote — do NOT include the 'Rather Listen' box or author bio, those are added separately",
  "scripture_reference": "e.g. 'Psalm 29:1-11'"
}}

The article_body_html should be substantial (roughly 900-1400 words), theologically careful, and never \
claim to quote something the pastor said that wasn't provided to you as source material."""


def draft_article_with_claude(sermon: dict, template_html: str, example_article_html: str) -> dict:
    client = Anthropic()
    prompt = build_prompt(sermon, template_html, example_article_html)

    message = client.messages.create(
        model="claude-opus-4-1-20250805",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(text)


def render_article_html(template_html: str, sermon: dict, slug: str, draft: dict) -> str:
    hero_image_url = "https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1600&auto=format&fit=crop"

    replacements = {
        "{{ARTICLE_TITLE}}": draft["article_title"],
        "{{ARTICLE_DESCRIPTION}}": draft["article_description"],
        "{{ARTICLE_SLUG}}": slug,
        "{{HERO_IMAGE_URL}}": hero_image_url,
        "{{HERO_IMAGE_ALT}}": draft["hero_image_alt"],
        "{{HERO_CAPTION}}": draft["hero_caption"],
        "{{KICKER}}": draft["kicker"],
        "{{DECK}}": draft["deck"],
        "{{ARTICLE_BODY_HTML}}": draft["article_body_html"],
        "{{SERMON_TITLE}}": sermon["title"],
        "{{SCRIPTURE_REFERENCE}}": draft.get("scripture_reference", sermon["title"]),
        "{{SERMON_DATE}}": sermon["date_display"],
        "{{SERMONAUDIO_URL}}": sermon["sermonaudio_url"],
        "{{CURRENT_YEAR}}": str(datetime.now(timezone.utc).year),
    }
    html = template_html
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=True, **kwargs)


def open_pull_request_for_sermon(sermon: dict, data: dict) -> None:
    base_slug = slugify(sermon["title"])
    existing_slugs = {a.get("slug") for a in data["articles"]}
    slug = base_slug
    if slug in existing_slugs and sermon.get("date_iso"):
        slug = f"{base_slug}-{sermon['date_iso']}"
    suffix = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template_html = f.read()

    example_path = os.path.join(
        REPO_ROOT, "what-does-the-bible-say-about-the-parable-of-the-sower.html"
    )
    example_article_html = ""
    if os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as f:
            example_article_html = f.read()

    draft = draft_article_with_claude(sermon, template_html, example_article_html)
    article_html = render_article_html(template_html, sermon, slug, draft)

    branch = f"new-article/{slug}"
    run(["git", "config", "user.name", "sermon-article-bot"])
    run(["git", "config", "user.email", "actions@users.noreply.github.com"])
    run(["git", "checkout", "-b", branch])

    article_path = os.path.join(REPO_ROOT, f"{slug}.html")
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(article_html)

    data["articles"].append(
        {
            "slug": slug,
            "title": draft["article_title"],
            "scripture": draft.get("scripture_reference", sermon["title"]),
            "date": sermon["date_iso"],
            "date_display": sermon["date_display"],
            "sermonaudio_url": sermon["sermonaudio_url"],
            "guid": sermon["guid"],
        }
    )
    save_articles_data(data)
    rebuild_index(data)

    run(["git", "add", f"{slug}.html", "articles-data.json", "index.html"])
    run(["git", "commit", "-m", f"New sermon article: {draft['article_title']}"])
    run(["git", "push", "-u", "origin", branch])

    has_description = bool(sermon["description"].strip())
    review_note = (
        "This sermon had no written description in the feed, so the article was written "
        "directly from the scripture passage, title, and series — please read closely to confirm "
        "it reflects what you actually preached."
        if not has_description
        else "This sermon included a written description, which was used as source material for the draft."
    )

    pr_body = f"""A new sermon was found on the SermonAudio feed: **{sermon['title']}** ({sermon['date_display']}).

An AI-drafted article is attached for your review. Nothing is published until you merge this pull request.

**{review_note}**

- Draft title: {draft['article_title']}
- Scripture: {draft.get('scripture_reference', sermon['title'])}
- Listen: {sermon['sermonaudio_url']}

To publish: click **Merge pull request**. To request changes: leave a comment. To skip this sermon: click **Close pull request**.
"""

    run(
        [
            "gh",
            "pr",
            "create",
            "--title",
            f"New article: {draft['article_title']}",
            "--body",
            pr_body,
            "--base",
            "main",
            "--head",
            branch,
        ]
    )

    run(["git", "checkout", "main"])


def main() -> None:
    sermons = fetch_feed()
    data = load_articles_data()
    known_guids = {a.get("guid") for a in data["articles"] if a.get("guid")}
    known_urls = {a.get("sermonaudio_url") for a in data["articles"] if a.get("sermonaudio_url")}

    new_sermons = [
        s for s in sermons if s["guid"] not in known_guids and s["sermonaudio_url"] not in known_urls
    ]

    if not new_sermons:
        print("No new sermons found. Nothing to do.")
        return

    print(f"Found {len(new_sermons)} new sermon(s). Drafting articles...")
    for sermon in new_sermons:
        try:
            print(f"Drafting: {sermon['title']}")
            open_pull_request_for_sermon(sermon, data)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to draft article for '{sermon['title']}': {exc}", file=sys.stderr)
            run(["git", "checkout", "main"])
            continue


if __name__ == "__main__":
    main()
