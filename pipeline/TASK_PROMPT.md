# Weekly task: turn new sermons into articles

You are a recurring background task for articles.wordandhope.com. Nobody is watching. Do not ask
questions. Take the most reasonable reading, say which one you took in your final report, and carry on.
If something is unrecoverable, finish what you can and say so at the end. Never print or repeat any token.

Repository: `schaefercmatthew/sermons-wordandhope`, attached to the session with push access.
Clone it (`git clone --depth 1`) and work from the repository root. Use git, not the REST API.

The site deploys to Cloudflare Pages from `main` through a GitHub Action. Pushing to `main` publishes.

## 1. Find new transcripts

A GitHub Action commits one file per sermon to `transcripts/` each day. Header format:
`SERMON_TITLE`, `SERIES`, `DATE_PREACHED`, `SERMONAUDIO_URL`, `SLUG`, `DATE_ISO`, `GUID`, then `---`, then the transcript.

A transcript is new when `articles/<slug>.html` does not exist. Skip, and list in the report, any that
- match an existing article's `sermonaudio_url` in `articles-data.json` under a different slug (duplicate),
- have a slug very close to an existing slug (possible duplicate),
- have a body that says no transcript is available. Never write from Scripture alone.

Process at most 3, oldest `DATE_ISO` first. If none are new, stop and report.

## 2. Draft each article

Read `pipeline/VOICE_RULES.md` completely and follow it. The article is the sermon, edited. Read
`article-template.html` and one recent article in `articles/` for the HTML conventions (sections, h2,
`blockquote.verse` with `cite`, optional `p.pull`).

Write the body HTML to a scratch file, then write `pipeline/meta/<slug>.json`. Copy the shape of
`pipeline/meta/psalm-73-1-28.json`. Field rules:
- `title`: a hook people would click, then the Scripture reference. Vary the format from recent articles.
- `description`: under 160 characters. `deck`: under 200 characters.
- `kicker`: "Series &middot; Theme" (HTML entities allowed).
- `tags`: one to three, copied exactly from the live filter buttons in `index.html` (`data-filter`). `update_site.py` rejects others.
- `verse_quote` / `verse_ref`: one or two sentences already quoted in the article, ESV.
- `image_base`, `hero_alt`, `hero_caption`: run `python3 scripts/pick_image.py rank <theme words>` and choose. Prefer UNUSED photos.
  The sandbox cannot load images, so never invent a new image URL. If only used photos fit, reuse the best match and say so in the report.

## 3. Build and check

```
python3 scripts/build_article.py pipeline/meta/<slug>.json <body.html> articles/<slug>.html
python3 scripts/check_article.py articles/<slug>.html transcripts/<slug>.txt
```
Fix the draft and rebuild until the script says PASS (at most 5 rounds). Write `pipeline/notes/<slug>.md`:
every correction to his wording, every cut point or illustration, and anything loosely traced.

## 4. Independent review

Spawn a fresh agent (new one each round) with the instructions in `pipeline/REVIEWER_PROMPT.md` and the paths to the
rules, transcript, article, check output, and notes. It must not edit files. Fix every BLOCKER yourself and re-review
with a new agent, at most 2 fix rounds. The reviewer is a gate, not a suggestion.

## 5. Publish or hold

PASS: run
```
python3 scripts/update_site.py publish <slug>
python3 scripts/update_site.py check     # must print "site is consistent"
```
Commit the article, meta, notes, `articles-data.json`, `index.html`, and `sitemap.xml` together in one commit and push to `main`.
Commit message: `Add article: <title>` and a line `Checks: script PASS, reviewer PASS`.
Afterward run `gh run list --limit 3` if `gh` works and report whether the deploy succeeded.

Still FAIL after the fix rounds: do not touch `main`. Push a branch `review/<slug>` containing the draft, notes, and the
reviewer's findings, and carry on with the next transcript.

## 6. Report

- Transcripts found, articles published (with the URL `https://articles.wordandhope.com/<slug>.html`), held for review (branch names), skipped and why.
- Every correction to Matthew's own wording from the notes files. He must confirm these.
- Any reviewer WARNINGS, any reused hero image, and any deploy problem.
