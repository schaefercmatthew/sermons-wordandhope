#!/usr/bin/env python3
"""Choose a hero image from photos already live on the site.

  pick_image.py rank WORD [WORD ...]   list candidate photos, best match first, with where each is already used
  pick_image.py rebuild                rebuild pipeline/images.json from the current articles

New photos can only be added after someone confirms the URL loads in a browser:
  pick_image.py add IMAGE_BASE_URL "alt text" "theme words"
The sandbox cannot reach images.unsplash.com, so nothing here fetches an image.
"""
import glob
import json
import os
import re
import sys

CAT = "pipeline/images.json"


def rebuild():
    data = json.load(open("articles-data.json", encoding="utf-8"))["articles"]
    cat = {}
    for a in data:
        base = a["image"].split("?")[0]
        alt = ""
        p = f"articles/{a['slug']}.html"
        if os.path.exists(p):
            m = re.search(r'<figure class="hero">\s*<img[^>]*alt="([^"]*)"', open(p, encoding="utf-8").read())
            alt = m.group(1) if m else ""
        e = cat.setdefault(base, {"image_base": base, "alt": alt, "themes": "", "used_by": []})
        e["used_by"].append(a["slug"])
        e["themes"] += " " + a["title"] + " " + a["topic"] + " " + a["tags"]
        e["alt"] = e["alt"] or alt
    old = {}
    if os.path.exists(CAT):
        old = {e["image_base"]: e for e in json.load(open(CAT))}
    for base, e in cat.items():
        if base in old and old[base].get("extra_themes"):
            e["extra_themes"] = old[base]["extra_themes"]
    for base, e in old.items():
        if base not in cat:  # catalogued but not yet used
            cat[base] = e
    json.dump(list(cat.values()), open(CAT, "w"), indent=1, ensure_ascii=False)
    print(len(cat), "photos in catalog")


def rank(words):
    cat = json.load(open(CAT))
    ws = {w.lower() for w in words}
    scored = []
    for e in cat:
        text = (e.get("themes", "") + " " + e.get("alt", "") + " " + e.get("extra_themes", "")).lower()
        score = sum(1 for w in ws if w in text)
        scored.append((len(e["used_by"]) == 0, score, -len(e["used_by"]), e))
    scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    for unused, score, _, e in scored[:8]:
        print(f"{'UNUSED' if unused else 'used x' + str(len(e['used_by']))} | match {score} | {e['image_base']}\n    {e['alt']}")


def add(base, alt, themes):
    cat = json.load(open(CAT))
    cat.append({"image_base": base.split("?")[0], "alt": alt, "themes": "", "extra_themes": themes, "used_by": []})
    json.dump(cat, open(CAT, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "rebuild":
        rebuild()
    elif c == "rank":
        rank(sys.argv[2:])
    elif c == "add":
        add(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
