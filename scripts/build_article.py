#!/usr/bin/env python3
"""Fill article-template.html from a metadata JSON and a body HTML file.

Usage: build_article.py META.json BODY.html OUT.html
META keys: title, description, slug, image_base (or image_local: true for a generated verse card), date_iso, hero_alt, hero_caption, kicker, deck,
           sermon_title, scripture, sermon_date, sermonaudio_url
"""
import datetime
import html
import json
import sys

meta = json.load(open(sys.argv[1], encoding="utf-8"))
body = open(sys.argv[2], encoding="utf-8").read().strip()
tpl = open("article-template.html", encoding="utf-8").read()

esc = lambda s: html.escape(s, quote=True)
vals = {
    "ARTICLE_TITLE": esc(meta["title"]),
    "ARTICLE_DESCRIPTION": esc(meta["description"]),
    "ARTICLE_SLUG": meta["slug"],
    "HERO_IMAGE_URL": ("https://articles.wordandhope.com/assets/heroes/" + meta["slug"] + ".png") if meta.get("image_local")
                      else meta["image_base"] + "?auto=format&fit=crop&w=1600&q=80",
    "DATE_ISO": meta["date_iso"],
    "HERO_IMAGE_ALT": esc(meta["hero_alt"]),
    "HERO_CAPTION": meta["hero_caption"],
    "KICKER": meta["kicker"],
    "DECK": esc(meta["deck"]),
    "SERMON_TITLE": esc(meta["sermon_title"]),
    "SCRIPTURE_REFERENCE": esc(meta["scripture"]),
    "SERMON_DATE": esc(meta["sermon_date"]),
    "SERMONAUDIO_URL": meta["sermonaudio_url"],
    "CURRENT_YEAR": str(datetime.date.today().year),
}
out = tpl.replace("{{ARTICLE_BODY_HTML}}", body)
for k, v in vals.items():
    out = out.replace("{{" + k + "}}", v)
left = [x for x in __import__("re").findall(r"\{\{[A-Z_]+\}\}", out)]
if left:
    sys.exit(f"unfilled placeholders: {left}")
open(sys.argv[3], "w", encoding="utf-8").write(out)
print("wrote", sys.argv[3])
