#!/usr/bin/env python3
"""Deterministic pre-publish checks for sermon articles.

Usage: check_article.py ARTICLE.html TRANSCRIPT.txt [--min-words N] [--max-words N]
Exit code 0 = no hard failures, 1 = at least one hard failure.
Judgment checks (faithfulness, voice, ESV accuracy) are done by the reviewer agent.
"""
import argparse
import html
import re
import sys

BANNED = [
    "it is worth noting", "it's worth noting", "worth noting", "in conclusion", "delves into",
    "delve into", "at its core", "journey", "tapestry", "navigate", "stands as a testament",
    "in today's world", "reminder that", "let us", "invites us", "beckons", "underscores",
    "speaks to", "shines a light", "shine a light", "calls us to", "challenges us to",
    "reminds us that", "that matters",
]
META = [
    r"\bnotice (that|how|what|something|whose|who|the)\b", r"^notice\b", r"\bnote that\b",
    r"\bobserve that\b", r"\bconsider this\b", r"\bhere is the thing\b",
]
BAD_OPENERS = [r"^throughout history", r"^in a world where", r"^the book of\b"]
MIRROR = re.compile(
    r"\b(?:it'?s|it is|this is|that is)\s+not\s+(?:just\s+)?[^.?!;]{1,80}?[,;]\s*(?:but|it'?s|it is)\b",
    re.I,
)
FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'll|I'd|my|me|mine|myself)\b")


CONTR = [("n't", " not"), ("'ve", " have"), ("'re", " are"), ("'ll", " will"), ("'m", " am"), ("'d", " would")]


def words(text):
    t = text.lower().replace("\u2019", "'")
    t = t.replace("won't", "will not").replace("can't", "can not")
    for a_, b_ in CONTR:
        t = t.replace(a_, b_)
    t = re.sub(r"\b(he|she|it|that|there|what|who|here|let)'s\b", r"\1 is", t)
    return re.findall(r"[a-z0-9]+", t)


def trigrams(ws):
    return {tuple(ws[i:i + 3]) for i in range(len(ws) - 2)}


def strip_tags(s):
    s = re.sub(r"</(p|h2|h3|li|blockquote|cite|figcaption)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("transcript")
    ap.add_argument("--min-words", type=int, default=900)
    ap.add_argument("--max-words", type=int, default=1400)
    ap.add_argument("--min-overlap", type=float, default=0.55)
    a = ap.parse_args()

    page = open(a.article, encoding="utf-8").read()
    m = re.search(r'<article class="body">(.*?)</article>', page, re.S)
    if not m:
        print("FAIL: no <article class=\"body\"> found")
        return 1
    body = m.group(1).split('<hr class="rule">')[0]

    tr = open(a.transcript, encoding="utf-8").read().split("\n---\n", 1)[-1]
    tr_tri = trigrams(words(tr))

    fails, warns = [], []

    # strip quotes (verses, confession) for prose-only checks
    quotes = re.findall(r"<blockquote.*?</blockquote>", body, re.S)
    prose_html = re.sub(r"<blockquote.*?</blockquote>", "", body, flags=re.S)
    prose_html = re.sub(r"<figure.*?</figure>", "", prose_html, flags=re.S)
    prose = strip_tags(prose_html)
    full_text = strip_tags(body) + "\n" + strip_tags(page.split("</article>")[0][:2500])

    # dashes
    head_html = page[:page.index('<article class="body">')]
    head_text = " ".join(x for t in re.findall(r'content="([^"]*)"|<title>([^<]*)</title>|<h1>([^<]*)</h1>|<p class="deck">([^<]*)</p>', head_html) for x in t if x)
    for label, chunk in (("body", body), ("title/meta/deck", head_text)):
        if re.search("\u2014|&mdash;|&#8212;", chunk):
            fails.append("em-dash present in " + label)
    for mm in re.finditer(r"\s[–-]\s", strip_tags(body)):
        fails.append("spaced dash used as connector near: ..." + strip_tags(body)[max(0, mm.start() - 30):mm.end() + 30].replace("\n", " "))

    low = prose.lower()
    for p in BANNED:
        if re.search(r"\b" + re.escape(p) + r"\b", low):
            fails.append(f"banned phrase: {p!r}")
    for p in META:
        for mm in re.finditer(p, low, re.M):
            fails.append(f"meta-commentary: {mm.group(0)!r}")
    if re.search(r"pastor matthew schaefer", strip_tags(page), re.I):
        fails.append('"Pastor Matthew Schaefer" used as a name')

    # opener
    paras = [strip_tags(p).strip() for p in re.findall(r"<p[^>]*>.*?</p>", prose_html, re.S)]
    paras = [p for p in paras if p]
    if paras:
        first = paras[0]
        first_sent = re.split(r"(?<=[.?!])\s", first)[0]
        if first_sent.endswith("?"):
            fails.append("opening sentence is a rhetorical question")
        for p in BAD_OPENERS:
            if re.search(p, first.lower()):
                fails.append(f"banned opener: {p}")

    # mirror constructions: "X is not A, but B", "He does not say A. He says B.", "..., and not B"
    mir = [m_.group(0) for m_ in MIRROR.finditer(prose)]
    flat = [x.strip() for p_ in paras for x in re.split(r"(?<=[.?!])\s+", p_) if x.strip()]
    neg = re.compile(r"\b(not|never|no one|n't)\b|n't\b", re.I)
    for s1, s2 in zip(flat, flat[1:]):
        w1, w2 = words(s1), words(s2)
        if (neg.search(s1) and not neg.search(s2) and len(w1) <= 24 and w1 and w2
                and w1[0] == w2[0] and w1[0] in {"he", "she", "it", "they", "this", "that", "you", "we", "i", "asaph", "job"}):
            mir.append(s1 + " / " + s2)
    mir += re.findall(r"[^.?!]*,\s*and not\s[^.?!]*", prose)
    if len(mir) > 1:
        fails.append(f"'not X, but Y' pattern used {len(mir)} times (max 1): " + " || ".join(m_.strip()[:90] for m_ in mir))
    elif mir:
        warns.append("one 'not X, but Y' pattern present")

    # colons
    colons = len(re.findall(r"(?<!\d):(?!\d)", prose))
    if colons > 6:
        warns.append(f"{colons} colons in prose (rule: rare)")

    # structure
    sections = re.findall(r"<section.*?</section>", body, re.S)
    h2s = len(re.findall(r"<h2", body))
    if not 3 <= h2s <= 5:
        fails.append(f"{h2s} h2 sections (need 3 to 5)")
    if sections and not re.search(r'<blockquote class="verse"', sections[0]):
        fails.append("first section lacks blockquote.verse")
    for q in quotes:
        if "<cite>" not in q:
            fails.append("blockquote without <cite>")

    # length (prose + quotes, body only)
    n = len(words(strip_tags(body)))
    if not a.min_words <= n <= a.max_words:
        fails.append(f"body is {n} words (allowed {a.min_words} to {a.max_words})")

    # provenance
    sents = [s.strip() for p in paras for s in re.split(r"(?<=[.?!])\s+", p) if len(words(s)) >= 6]
    untraced_fp, loose = [], []
    tot = hit = 0
    for s in sents:
        t = trigrams(words(s))
        if not t:
            continue
        cov = len(t & tr_tri) / len(t)
        tot += len(t)
        hit += len(t & tr_tri)
        if FIRST_PERSON.search(s) and cov < 0.35:
            untraced_fp.append((round(cov, 2), s))
        elif cov < 0.25:
            loose.append((round(cov, 2), s))
    overall = hit / tot if tot else 0
    if overall < a.min_overlap:
        fails.append(f"only {overall:.0%} of prose wording comes from the transcript (need {a.min_overlap:.0%})")
    for cov, s in untraced_fp:
        fails.append(f"first-person sentence not traceable to transcript (overlap {cov}): {s}")
    for cov, s in loose:
        warns.append(f"loosely traced sentence (overlap {cov}): {s}")

    print(f"words: {n} | h2 sections: {h2s} | transcript overlap: {overall:.0%}")
    for w in warns:
        print("WARN:", w)
    for f in fails:
        print("FAIL:", f)
    print("RESULT:", "FAIL" if fails else "PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
