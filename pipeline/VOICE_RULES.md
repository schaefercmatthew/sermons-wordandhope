# Article voice rules (Matthew Schaefer)

These rules govern every sermon article. The drafter follows them, `scripts/check_article.py`
enforces what a script can enforce, and an independent reviewer agent
(`pipeline/REVIEWER_PROMPT.md`) checks the rest before anything is published.

## The principle

The article is the sermon, edited. It is not a new piece written about the sermon.
The transcript is the base text. Keep Matthew's own sentences and illustrations wherever
possible. Change only what spoken delivery requires: filler words, false starts, repeated
phrases, pulpit-only references ("turn with me"), and anything tied to the day it was preached.

## What the drafter does

1. Clean the spoken artifacts (um, uh, "you know", restarts, mid-sentence corrections).
2. Reorder only as needed to make a 3 to 5 section article. Section order should follow the passage.
3. Length is not a constraint. Include everything that carries the argument. If something must be
   cut for readability, drop a whole point and log it in the notes. Never compress it into a summary.
   Summaries are the main way voice gets lost. Cut a whole point before you compress it.
4. Keep every illustration Matthew used that carries weight (the hike, the goat, the toddler).
   If an illustration has to go, say so in the notes file.
5. Keep his Scripture references, confession citations, and cross-references. Do not add
   Scripture, quotations, historical claims, or theology he did not use.
6. Quote Scripture in the ESV inside `blockquote.verse` with a `cite` line. Where the transcript
   reading is garbled by transcription, restore the ESV wording. Never rewrite a verse.
7. If Matthew misspoke (wrong quotation, wrong verse), fix it quietly and list the fix in the notes file.
8. Make it evergreen. Replace "this morning", "next week", "on Thursday" with wording that
   still reads correctly a year later.

## What the drafter must never do

- Invent a personal story, confession, experience, or "I have..." statement. Every first-person
  claim and every illustration must trace to the transcript. If Matthew said it as a hypothetical
  ("Look, I served faithfully for years..."), keep it clearly framed as a hypothetical.
- Add a conclusion, application, or theological claim he did not make.
- Refer to Matthew in the third person in the body, or call him "Pastor Matthew Schaefer".
- Use local or private details known only to the congregation (names of families, local places).
  Replace with a universal image or drop the detail.

## Voice

Short declarative sentences. Direct pastoral address ("you"). Concrete images over abstraction.
Reformed grounding, held lightly. The congregation is not debate-minded, so exposition
leads to comfort and application, not combat. He is honest about doubt and about his own sin.
He names a hard thing plainly and then answers it from the text.

## Hard fails (the script checks these)

- No em-dashes anywhere in the title, description, deck, or body. (The shared site footer in
  `article-template.html` has one. Matthew chose to keep it; do not change it.) No spaced en-dashes used as connectors. En-dashes are allowed only
  in number ranges (Psalm 73:3–12).
- None of these phrases: "it is worth noting", "worth noting", "in conclusion", "delves into",
  "at its core", "journey" (metaphorical), "tapestry", "navigate", "stands as a testament",
  "in today's world", "reminder that", "let us", "invites us", "beckons", "underscores",
  "speaks to", "shines a light", "calls us to", "challenges us to", "reminds us that",
  "that matters".
- No meta-commentary that points at the writing: "notice that", "notice how", "notice something",
  "note that", "observe that", "consider this".
- No opening paragraph that starts with a rhetorical question, "Throughout history",
  "In a world where", or "The book of".
- No "not X, but Y" / "it's not X, it's Y" contrast that the drafter added. Contrasts Matthew
  himself preached are kept as he said them (decision from Matthew, Nov 25).
- Colons are rare in prose. The script warns above 6.
- Every first-person sentence must be traceable to the transcript.
- Most of the article's wording must come from the transcript (overlap threshold in the script).
- Structure: an opening section with no heading that contains a `blockquote.verse` with `cite`,
  then 3 to 5 sections each with an h2. "Matthew Schaefer" only as a name.

## Judgment checks (the reviewer agent does these)

- Is anything in the article not supported by the transcript or the passage?
- Does any sentence summarize the passage instead of making Matthew's argument?
- Is there motivational-poster spirituality not tied to the text?
- Do the ESV quotations match the ESV? Are references right?
- Is the sermon's argument faithfully preserved, including its gospel turn?
- Does it sound like Matthew speaking, or like generic Christian writing?
- Were any illustrations or confession citations dropped without a note?

## Notes file

Each draft ships with `pipeline/notes/<slug>.md` listing: corrections to Matthew's wording, illustrations or points cut, and any
sentence the checker flagged as only loosely traceable.
