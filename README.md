# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

Student knowledge about the **Tufts University Computer Science department** — which
professors are worth taking, how hard specific courses are, what the real workload is,
and how to sequence the major. This knowledge is valuable because the official course
catalog and department pages describe *what* a class covers but never *what it's like*:
teaching style, exam difficulty, time commitment, or whether a professor gives useful
feedback. That information lives only in student-to-student channels — Rate My
Professors reviews and r/Tufts threads — which are scattered, unstructured, and
contradictory. This system makes that informal knowledge searchable and answerable
with citations.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate My Professors — Milod Kazerounian | Professor reviews | https://www.ratemyprofessors.com/professor/2685422 → `documents/rmp_kazerounian.txt` |
| 2 | Rate My Professors — Mark Sheldon | Professor reviews | https://www.ratemyprofessors.com/professor/1762218 → `documents/rmp_sheldon.txt` |
| 3 | Rate My Professors — Ming Chow | Professor reviews | https://www.ratemyprofessors.com/professor/1499073 → `documents/rmp_chow.txt` |
| 4 | Rate My Professors — David Lillethun | Professor reviews | https://www.ratemyprofessors.com/professor/2647589 → `documents/rmp_lillethun.txt` |
| 5 | Rate My Professors — Noah Mendelsohn | Professor reviews | https://www.ratemyprofessors.com/professor/1873452 → `documents/rmp_mendelsohn.txt` |
| 6 | Rate My Professors — Fabrizio Santini | Professor reviews | https://www.ratemyprofessors.com/professor/2708190 → `documents/rmp_santini.txt` |
| 7 | Rate My Professors — Karen Edwards | Professor reviews | https://www.ratemyprofessors.com/professor/2434239 → `documents/rmp_edwards.txt` |
| 8 | r/Tufts — "CS in School of Science vs School of Engineering" | Reddit thread | https://www.reddit.com/r/Tufts/comments/1hqebvg/ → `documents/reddit_science_vs_eng.txt` |
| 9 | Tufts Admissions "Jumbo Talk" — Why CS at Tufts | Student blog article | https://admissions.tufts.edu/blogs/jumbo-talk/post/why-cs-at-tufts/ → `documents/article_why_cs_tufts.txt` |
| 10 | r/Tufts — "Which CS courses should I take, in what order?" | Reddit thread | https://www.reddit.com/r/Tufts/comments/k0li59/ → `documents/reddit_course_order.txt` |

Sources are recorded with full metadata (type + URL + local file) in `sources.json`,
which the ingestion pipeline reads. **Collection method:** because Rate My Professors is
JavaScript-rendered and Reddit blocks automated scrapers, the raw text for each source
was saved by hand into the `documents/` folder rather than scraped live. `ingest.py`
then loads and cleans those files.

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** Routed by source type — there is no single uniform size, because the
corpus mixes short independent opinions with continuous prose.
- *RMP reviews & Reddit comments:* one segment = one chunk (no fixed size; ~300–450
  characters in practice). Segments are marked by a hard delimiter line (`----`) placed
  between each review/comment.
- *Articles & long Reddit posts:* a sliding window of **1,600 characters** (~400 tokens).
- *Safety net:* any delimited segment longer than 1,600 characters is sub-split with the
  same window so no chunk is unbounded.

**Overlap:**
- *Reviews/comments:* **0** — each is a complete, self-contained opinion; overlap would
  only bleed one student's words into another's.
- *Articles/long posts:* **240 characters (~15%)**, so an idea split mid-paragraph still
  appears whole in at least one chunk. Windows prefer to break on a paragraph or sentence
  boundary rather than mid-word.

**Why these choices fit your documents:** A Rate My Professors page is many tiny,
independent reviews that often contradict each other ("best prof at Tufts" vs. "worst
class I took"). Splitting on a fixed character count would merge two students into one
chunk and let the system cite a contradiction as a single voice — so each review is kept
whole and separate. Reddit threads are hybrids: the original post is article-like
(chunked with overlap) while each comment is review-like (kept whole). The Jumbo Talk
article is continuous prose where one idea spans a paragraph, so it needs larger,
overlapping windows. Each chunk also carries its source `name` and `url` as metadata,
which both restores context to a tiny review chunk and provides source attribution.

**Preprocessing before chunking:** `ingest.py` normalizes line endings, strips
trailing whitespace, and collapses large blank-line gaps. Manual delimiter lines
(`----`) were inserted between reviews/comments to mark hard boundaries. (Inputs were
hand-saved text, so no HTML/nav stripping was needed.)

**Final chunk count:** **44 chunks** across 10 documents — 35 from the 7 RMP pages
(1 rating-summary header + 4 reviews each), 7 from the 2 Reddit threads (each post +
its comments), and 2 from the article.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, with vectors stored in
ChromaDB using cosine similarity. I chose it because it runs **locally** with no API key,
no rate limits, and no cost; it is fast; and its 384-dimension embeddings are more than
enough for a 44-chunk corpus. Its 256-token input limit comfortably fits our chunks
(reviews are tiny, and article chunks are capped at ~400 tokens). In retrieval testing it
ranked the correct source chunk #1 for every in-corpus eval question (distances 0.35–0.48).

**Production tradeoff reflection:** If this were deployed for real users and cost weren't
a constraint, I'd weigh:
- **Accuracy on domain text** — a larger API model (e.g. OpenAI `text-embedding-3-large`
  or Cohere `embed-v3`) embeds nuanced, sarcastic student opinions more accurately. Our
  one retrieval failure (see Failure Case) was an embedding-dilution problem a stronger
  model might partly mitigate.
- **Context length** — MiniLM truncates at 256 tokens. A model with an 8k window could
  embed whole long reviews/articles without aggressive chunking, reducing information
  split across boundaries.
- **Local vs. API** — local (MiniLM) gives zero per-query cost, privacy, and offline use,
  but a lower quality ceiling. An API model improves quality at the cost of latency per
  call, ongoing spend, and a rate-limited external dependency.
- **Multilingual** — not needed here (the corpus is English-only), so I would *not* pay
  for a multilingual model — a case where the "better" model is wasted budget for this
  domain.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:** The system prompt in `generate.py` *enforces*
grounding rather than suggesting it. The model is told it may use ONLY the context block
provided in the user message (real student reviews/posts), must never use outside or
prior knowledge, and must not guess or generalize. Critically, if the context does not
contain enough information, it must reply with one exact sentence — *"I don't have enough
information on that."* — and nothing else. Generation runs at `temperature=0` to minimize
drift from the context. The retrieved chunks are passed as a numbered context block
(`[1] (source: ...) <text>`), and the model is instructed to cite the `[n]` labels it used.

**How source attribution is surfaced in the response:** Attribution is **guaranteed in
code, not trusted to the model.** After generation, `generate.py` parses the `[n]`
citations the model actually produced, maps each number back to the corresponding
retrieved chunk, de-duplicates by source, and returns a `sources` list of
`"name — url"` strings. The interface shows these under a "Retrieved from" panel. If the
model declines (returns the exact no-information sentence), the source list is empty, so
the system never attributes a non-answer to a document. This means even if the model
forgot to cite, attribution is still derived programmatically from the retrieved set
(fallback), and when it does cite, attribution is precise to the sources used rather than
every chunk retrieved.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

These 5 questions deliberately cover all three source types — RMP reviews (Q1–3), a
Reddit thread (Q4), and the article (Q5) — so evaluation exercises the whole corpus. The
"Top chunk retrieved" column shows the highest-ranked chunk and its cosine distance
(lower = closer match).

| # | Question | Expected answer | System response (summarized) | Top chunk retrieved (distance) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|--------------------------------|-------------------|-------------------|
| 1 | Is Ming Chow's class considered an easy A? | Yes — reviews call it a low-stress easy A. | "According to [1], Ming Chow's COMP116 is a 'low-stress easy A' (difficulty 2.0); [3] rates COMP28 difficulty 1.0." Cites Ming Chow. | Ming Chow review (0.405) | Relevant | Accurate |
| 2 | Which CS professor do students rate most highly, and why? | Milod Kazerounian — "best CS professor at Tufts": caring, accommodating, engaging. | "Students rate Milod Kazerounian most highly — 5.0 quality in [1][2][4]; one calls him 'the best CS professor at Tufts.'" Cites Kazerounian. | Kazerounian review (0.472) | Relevant | Accurate |
| 3 | How time-consuming is Mark Sheldon's class? | Very — "super time consuming," but you gain a lot. | "Mark Sheldon's COMP40 is 'super time consuming' but you 'gain so much from it' [2]." Cites Sheldon. | Sheldon review (0.476) | Relevant | Accurate |
| 4 | Do engineering students get priority registration over A&S CS students? | Yes — they register first, so A&S CS students get shut out of classes. | "Yes, [1] says engineering students are given preference and register ahead of A&S CS students." Cites the Reddit thread. | Reddit "Science vs Eng" (0.425) | Relevant | Accurate |
| 5 | Why does Tufts CS start with C++ instead of Java/Python? | Because C++ is lower-level and teaches memory/abstraction; reinforced by CS40 in C. | "Because C++ is lower-level and teaches how memory works plus abstraction and modularity [1]." Cites the article. | "Why CS at Tufts" article (0.351) | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

**Grounding spot-check (out-of-scope query):** Asked a question the corpus does not cover —
*"What is the meal plan like at the Tufts dining halls?"* — the system returned exactly
*"I don't have enough information on that."* with **no sources**, instead of inventing a
plausible answer from general knowledge. This confirms grounding holds on off-domain queries.

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** "Can you resubmit assignments in David Lillethun's class?"
(found during retrieval testing; not one of the final 5 demo questions).

**What the system returned:** *"I don't have enough information on that."* — even though
the correct answer exists almost verbatim in the corpus: a Lillethun review states *"All
assignments can be resubmitted if it was not correct the first time, so it's a low stress
class."* That chunk ranks **#22 of 44 (cosine distance 0.707, a weak match)** and never
reaches the top-5 passed to the LLM, so the model only sees other Lillethun reviews (about
grading turnaround time). Notably, the generation stage handles this *gracefully* — it
declines rather than hallucinating an answer — so the failure is isolated to retrieval.

**Root cause (tied to a specific pipeline stage):** Embedding dilution at the **chunking
stage**. Our deliberate rule is "1 review = 1 chunk" so each review stays whole. But that
particular review is *mostly about* boring lectures, intro-to-OS content, and textbook
readings, and only mentions resubmission in one trailing clause. The chunk embedding is an
average over the whole text, so the lone resubmission signal is washed out by the
surrounding topics. This is a retrieval failure, **not** a wording failure: I tested four
rephrasings of the query (including "Is Lillethun's class low stress?", which matches the
chunk's own words) and the resubmit chunk never reached the top-3 in any of them.

**What you would change to fix it:** Move to sentence- or clause-level chunking (or add
sentence-level sub-chunks alongside the whole-review chunks) so a single strong sentence
like the resubmission clause gets its own embedding and isn't diluted. The trade-off is
that this sacrifices the surrounding context that keeping whole reviews provides — and
risks the contradiction-merging problem the whole-review rule was designed to avoid — so
it's a genuine design tension, not a free win. A stronger/larger embedding model might
also partly mitigate the dilution.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** Writing the Chunking Strategy in
planning.md *before* coding forced the decision that the corpus has two structurally
different kinds of text — short independent opinions vs. continuous prose — and that one
uniform chunk size would be wrong. Because that reasoning was already written down,
`chunk.py` had a clear target: route by `source_type`, keep each review/comment whole,
and window only the article. Without the spec I likely would have defaulted to a single
"split every N characters" approach and merged contradicting reviews into one chunk.

**One way your implementation diverged from the spec, and why:** The spec described
Reddit and article chunking using a recursive splitter from `langchain-text-splitters`.
In practice I implemented the windowing in plain Python instead, because `langchain` was
not in the project's `requirements.txt` and adding a heavy dependency for one sliding
window wasn't worth it. The behavior still matches the spec (paragraph/sentence-preferred
breaks, ~1,600-char windows, ~15% overlap) — only the library changed. I also added a
"hard delimiter (`----`)" convention that wasn't in the original spec, because real RMP
pages needed an unambiguous review boundary that automatic splitting couldn't guarantee.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1 — Chunking implementation**

- *What I gave the AI:* My Chunking Strategy section from planning.md (route by source
  type; 1 review/comment = 1 chunk; ~1,600-char windowed chunks with 15% overlap for the
  article), plus samples of the actual document structure so it could see how RMP reviews
  and Reddit comments were laid out.
- *What it produced:* `chunk.py` with a unified design — split on a hard `----` delimiter
  for reviews/comments, window only the article, and a safety net that sub-splits any
  segment longer than the window.
- *What I changed or overrode:* I decided to insert the `----` delimiters into the source
  files myself rather than rely on the AI auto-detecting review boundaries from RMP's
  inconsistent formatting (one review even had a stray duplicated rating block). I also
  kept each RMP page's "Overall Quality" header as its own chunk because it carries the
  professor's aggregate rating, which is useful for "is X well-liked?" queries.

**Instance 2 — Diagnosing a weak eval question**

- *What I gave the AI:* Two eval questions whose retrieval looked weak ("Can you resubmit
  assignments in Lillethun's class?" and "Which professor gives the most useful
  feedback?"), and asked whether the problem was the *retrieval system* or just the
  *wording* of the questions.
- *What it produced:* A diagnostic that ran several rephrasings of each question plus some
  fresh questions on other source types, printing the top chunks and distances. It found
  the resubmit answer ranked #22/44 across *every* phrasing (a genuine embedding-dilution
  retrieval failure), while questions on the Reddit/article sources retrieved at distances
  as low as 0.23.
- *What I changed or overrode:* Instead of just swapping in easier questions, I kept the
  resubmit failure as my documented Failure Case (it's a real, well-evidenced bug), and
  replaced the two weak questions with cross-source questions so my final 5 exercise all
  three source types (RMP, Reddit, article) rather than only RMP.
