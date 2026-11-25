# Setup guide: Word & Hope sermon articles

## How it works

1. **Transcripts.** A GitHub Action (`.github/workflows/check-sermons.yml`) runs daily at 13:00 UTC. It checks
   SermonAudio for new sermons and commits their transcripts to `transcripts/`. It uses the repository secret
   `SERMONAUDIO_API_KEY`. No writing happens in this step.
2. **Articles.** A weekly Claude scheduled task follows `pipeline/TASK_PROMPT.md`. For each new transcript it
   edits the sermon into an article using `pipeline/VOICE_RULES.md`, runs `scripts/check_article.py`, has an
   independent reviewer agent check it, then publishes. If the reviewer will not pass it, nothing is published
   and a `review/<slug>` branch is pushed for you to read.
3. **Site updates.** `scripts/update_site.py publish <slug>` updates `articles-data.json`, the homepage card, the
   "Read the latest article" button, and `sitemap.xml` together, using `pipeline/meta/<slug>.json`.
4. **Deploy.** `.github/workflows/deploy.yml` deploys the repository to Cloudflare Pages on every push to `main`.
   It uses the repository secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
   `_redirects` is read by Cloudflare Pages.

## Where things live

| Item | Location |
|---|---|
| Voice rules | `pipeline/VOICE_RULES.md` |
| Reviewer instructions | `pipeline/REVIEWER_PROMPT.md` |
| Weekly task prompt | `pipeline/TASK_PROMPT.md` |
| Per-article metadata (tags, image, verse) | `pipeline/meta/` |
| Drafter notes (corrections to your wording, cuts) | `pipeline/notes/` |
| Hero photo catalog | `pipeline/images.json` (`scripts/pick_image.py`) |
| Article page template | `article-template.html` |
| Retired Plaud prompt | `pipeline/archive/` |

## Things to know

- **One address per article:** `https://articles.wordandhope.com/<slug>.html`. The canonical tags, sitemap, and homepage
  links all use it. The address without `.html` redirects to it (301) in `functions/[[path]].js`.
- **The sitemap Google reads** is served from `functions/_root-files.js`, a generated copy of `sitemap.xml`.
  `scripts/update_site.py` keeps the two in sync. Do not edit the copy by hand.

- Hero photos come from Unsplash and are chosen from photos already on the site. To add a new photo, confirm the
  URL loads in a browser, then run `python3 scripts/pick_image.py add <url> "alt text" "theme words"`.
- Homepage filter buttons are the source of truth for topic tags. A new tag needs a new button in `index.html` first.
- Check the whole site at any time with `python3 scripts/update_site.py check`.
- Hosting is Cloudflare Pages. An earlier version of this guide described Netlify, which this site no longer uses.
