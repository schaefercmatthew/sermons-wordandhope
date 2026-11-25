#!/usr/bin/env python3
"""Generate a branded verse card (hero, social preview, and homepage thumbnail) for an article.

  make_image.py pipeline/meta/SLUG.json [OUT_DIR]

Reads verse_quote, verse_ref, slug from the meta file. Writes OUT_DIR/SLUG.png (1600x900, used as the
hero and the social-share image) and OUT_DIR/SLUG-card.png (900x563, homepage card). The palette is picked
from the slug so every article differs but stays in the site's colors. No network access is needed.
"""
import hashlib
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
MARC = os.path.join(FONTS, "Marcellus-Regular.ttf")
PTI = os.path.join(FONTS, "PT_Serif-Web-Italic.ttf")
PTR = os.path.join(FONTS, "PT_Serif-Web-Regular.ttf")

# (background, verse text, accent, muted)
PALETTES = [
    ("#fbf7f0", "#241f1a", "#8a3324", "#52483e"),  # paper
    ("#f3ecdf", "#241f1a", "#8a3324", "#52483e"),  # warm paper
    ("#241f1a", "#fbf7f0", "#d9a577", "#c9beac"),  # ink
    ("#8a3324", "#fbf7f0", "#f6e6de", "#f0d5c8"),  # accent red
    ("#3a4a45", "#fbf7f0", "#e3c58f", "#cfd8d3"),  # deep green-grey
    ("#2f3a4a", "#fbf7f0", "#e3c58f", "#cdd3dc"),  # deep slate
]


def tracked(draw, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def wrap(draw, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def render(meta, W=1600, H=900):
    h = int(hashlib.sha256(meta["slug"].encode()).hexdigest(), 16)
    bg, ink, accent, muted = PALETTES[h % len(PALETTES)]
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([36, 36, W - 37, H - 37], outline=muted, width=1)
    left, width = 150, W - 300

    tracked(d, (left, 104), "WORD AND HOPE", ImageFont.truetype(PTR, 26), accent, 7)
    d.line([left, 156, left + 90, 156], fill=accent, width=3)

    quote = "“" + meta["verse_quote"].strip() + "”"
    top, bottom = 200, 700
    for size in range(96, 40, -2):
        f = ImageFont.truetype(MARC, size)
        lines = wrap(d, quote, f, width)
        lh = int(size * 1.28)
        if len(lines) * lh <= bottom - top and len(lines) <= 6:
            break
    block = len(lines) * lh
    y = top + (bottom - top - block) // 2
    for ln in lines:
        d.text((left, y), ln, font=f, fill=ink)
        y += lh

    d.text((left, 770), meta["verse_ref"] + " (ESV)", font=ImageFont.truetype(PTI, 40), fill=accent)
    right = "Matthew Schaefer"
    fr = ImageFont.truetype(PTR, 26)
    d.text((W - left - d.textlength(right, font=fr), 782), right, font=fr, fill=muted)
    return img


def main():
    meta = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else "assets/heroes"
    os.makedirs(out, exist_ok=True)
    img = render(meta)
    img.save(os.path.join(out, meta["slug"] + ".png"), optimize=True)
    img.resize((900, 563), Image.LANCZOS).save(os.path.join(out, meta["slug"] + "-card.png"), optimize=True)
    print("wrote", os.path.join(out, meta["slug"] + ".png"))


if __name__ == "__main__":
    main()
