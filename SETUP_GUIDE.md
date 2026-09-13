# Setup Guide — Sermons Word & Hope Automation

This picks up from where the repository and Netlify hosting were already connected. Everything below is what's needed to finish and keep the pipeline running.

## What this pipeline does

1. Every day, a GitHub Action checks SermonAudio for new sermons and downloads their transcripts into the repo's `/transcripts` folder. No AI writing happens in this step — it's a plain download.
2. A recurring Plaud scheduled task (set up in the step below) checks that same repo for any transcript that doesn't have a matching article yet, writes a polished article in your preaching voice, and publishes it to the site — updating the homepage automatically in the same run.
3. Netlify republishes the site automatically any time a file changes in the repo. There is nothing to click or deploy manually.

## Step 3 — Register the recurring Plaud scheduled task

This is the one piece that had to be created by hand. Set up a recurring Plaud scheduled task (daily is recommended) with the instructions already saved in the repo file `PLAUD_AGENT_INSTRUCTIONS.md`. Copy everything below the `---` line in that file into the task's instructions box, exactly as written — it already contains complete, tested steps for finding new transcripts, writing the article, and updating the homepage.

Suggested timing: run it daily, a few hours after the transcript-fetching GitHub Action runs (for example, once in the early morning), so it always has fresh transcripts ready when it checks. The exact time isn't critical — the task safely does nothing if there's nothing new to write.

## Step 4 — Nothing else to configure

- The `_redirects` file, the article template, and the homepage template are already in place and working — no changes needed.
- The GitHub Action that fetches transcripts is already correct and requires no edits.
- `articles-data.json` is the master list the homepage is built from; the scheduled task updates it automatically every time it publishes a new article.

## Current status (as of this write-up)

All 32 sermons currently on your SermonAudio page have been turned into published articles on the site, matching the tone and structure of your original sample article. The recurring task above will pick up automatically from here — any sermon posted after today will flow through the same pipeline without you doing anything.

## One thing that needs your attention

The live site is currently returning an "Unauthorized" (401) response on every page — including the homepage — when checked directly. This matches the behavior of Netlify's **Visitor Access** / **Edge Access** feature, which puts a login gate in front of the entire site. If that setting is turned on for this site, a visitor (or this automation, checking that pages loaded correctly) will see this login screen instead of the article.

To fix it: in the Netlify dashboard, open this site's **Site configuration → Visitor access**, and turn Visitor Access off (or add the right credentials if you want to keep it on for some other reason). This is not something that can be changed through the GitHub repository — it has to be done in Netlify's own settings, which only someone with access to your Netlify account can do.

Once that's turned off, every article link on the homepage should load normally for anyone who visits.
