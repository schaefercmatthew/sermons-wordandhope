# Contributing to sermons-wordandhope

This file explains how to make a few common changes to this site. It's written so that a
non-technical person — or an automated writing agent following `PLAUD_AGENT_INSTRUCTIONS.md` —
can make these changes correctly without needing to understand the rest of the codebase.

## How the topic filter works

The homepage (`index.html`) has a "What we write about" section with a row of clickable
buttons (Prayer, Sin & Repentance, The Gospels, and so on). Clicking one of these buttons
filters the article grid below it, showing only articles tagged with that category. Clicking
the same button again clears the filter and shows every article again.

This works using two things that have to stay in sync:

1. **The buttons themselves**, in `index.html`, inside `<section class="topics">`. Each button
   looks like this:
   ```html
   <button type="button" class="topic-chip" data-filter="Prayer">Prayer</button>
   ```
   The `data-filter` value is the category name. This is the complete, official list of
   categories — if a category isn't a button here, the filter doesn't know about it.

2. **Each article card's tags**, also in `index.html`, inside `<section class="library">`.
   Each article card looks like this:
   ```html
   <a class="article-card" href="/psalm-51.html" data-tags="Sin & Repentance, Prayer">
   ```
   The `data-tags` value lists every category that article belongs to, separated by commas.
   Most articles belong to just one category; some genuinely belong to two.

The filter's JavaScript (near the bottom of `index.html`, in the `<script>` block) reads
these two things automatically — it does not need to be changed when you add, remove, or
rename a category. It works by matching whatever `data-filter` was clicked against each
card's `data-tags`, and it already understands multiple comma-separated tags on one card.

## How to add a new filter category

Say you want to add a new category, for example "Church History."

1. **Add a new button.** In `index.html`, find `<section class="topics">` and add one more
   button inside `<div class="topic-list" id="topic-list">`, matching the existing style:
   ```html
   <button type="button" class="topic-chip" data-filter="Church History">Church History</button>
   ```
2. **Tag the articles that belong in it.** Find each `<a class="article-card" ...>` in
   `<section class="library">` whose article belongs in this new category, and add the
   category name to that card's `data-tags` attribute (comma-separated if the card already
   has another tag):
   ```html
   data-tags="Church History"
   ```
   or, if it already has a tag:
   ```html
   data-tags="Old Testament Narrative, Church History"
   ```
3. **That's it — no JavaScript changes needed.** The filter reads the button list and the
   card tags directly from the page each time it runs, so a new button and newly-tagged
   cards work immediately.
4. **Also update `articles-data.json`** so the new tag is preserved the next time an
   automated agent rebuilds the homepage grid (see `PLAUD_AGENT_INSTRUCTIONS.md`). Find the
   matching article's entry and update its `"tags"` field the same way:
   ```json
   "tags": "Old Testament Narrative, Church History"
   ```

### A few rules to keep the filter working correctly

- Category names must be spelled and capitalized **identically** everywhere they appear — in
  the button's `data-filter`, in every card's `data-tags`, and in `articles-data.json`'s
  `"tags"` field. "Church History" and "church history" are treated as two different
  categories by the filter.
- If a category name contains an ampersand (like "Suffering & Providence"), write it as
  `&amp;` inside `data-filter` and `data-tags` attributes in the HTML file — this is a plain
  HTML rule for attribute values, not something specific to the filter. In `articles-data.json`
  (a JSON file, not HTML), write it as a plain `&` instead.
- Removing a category means deleting its button and removing that tag from any card's
  `data-tags` — don't leave a card tagged with a category that no longer has a button, since
  it will just never be reachable by any filter click.
- Every article should have at least one tag. An article with no `data-tags` attribute at all
  will always be visible, no matter what filter is active — it's better to tag it with the
  closest fitting existing category (or "Christian Living" as a general fallback) than to
  leave it untagged.

## Where article tags come from when a new article is published

If you're publishing a new article by hand (not through the automated agent), decide which
category or categories the article's actual content belongs to — not its book or series name.
For example, an article on Philippians about contentment fits "Christian Living," not a
"Philippians" category, because "Philippians" isn't one of the site's filter categories.
Use the current list of category buttons in `index.html` as the source of truth for what's
available, choose from that list, and follow the two steps above (tag the card, and update
`articles-data.json`) to keep everything in sync.
