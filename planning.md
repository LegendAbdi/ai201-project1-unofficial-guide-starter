# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

Student knowledge about the Tufts CS department.which CS professors are worth taking, how hard specific courses are, what the workload is really like, and how to survive the major — the stuff students tell each other, not what the course catalog says.
5 questions this domain can answer (your checkpoint)
Which CS professor gives the most useful feedback?
How hard is CS 11 (Data Structures) and how much time does it take?
Is Ming Chow's class actually an easy A?
Which intro course should I take first as a CS major?
What's the jump from C++ to C like in CS 40?

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 |ratemyprofessor | Milod Kazerounian| https://www.ratemyprofessors.com/professor/2685422|
| 2 | ratemyprofessor|Mark Sheldon | https://www.ratemyprofessors.com/professor/1762218|
| 3 | ratemyprofessor| Ming Chow| https://www.ratemyprofessors.com/professor/1499073|
| 4 | ratemyprofessor| David Lillethun|https://www.ratemyprofessors.com/professor/2647589 |
| 5 | ratemyprofessor| Noah Mendelsohn| https://www.ratemyprofessors.com/professor/1873452|
| 6 | ratemyproffesor|Fabrizio Santini |https://www.ratemyprofessors.com/professor/2708190|
| 7 | ratemyproffesor| Karen Edwards| https://www.ratemyprofessors.com/professor/2434239|
| 8 | Reddit| Computer Science in School of Scienve vs School of engineering| https://www.reddit.com/r/Tufts/comments/1hqebvg/computer_science_in_school_of_scienve_vs_school/|
| 9 | Tufts admissions| Why CS at Tufts| https://admissions.tufts.edu/blogs/jumbo-talk/post/why-cs-at-tufts/|
| 10 | reddit| If I major in comp sci, which courses should I take in which order? (or any advice)| https://www.reddit.com/r/Tufts/comments/k0li59/if_i_major_in_comp_sci_which_courses_should_i/|

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

This corpus has two structurally different kinds of text, so we do **not** use one
uniform chunk size. We route each document type to a strategy that matches its natural
unit of meaning.

### Rate My Professors reviews (sources 1–7)

- **Chunk size:** one review per chunk (no fixed size). Each review is ~30–120 tokens.
- **Overlap:** 0.
- **Reasoning:** Each review is already a complete, self-contained opinion from one
  student. Cutting on a fixed character count would merge two students who disagree
  ("best prof at Tufts" + "worst class I took") into a single chunk, so an answer would
  cite a contradiction as one voice. There is no narrative running across reviews, so
  overlap would add noise with no benefit. We attach the professor name + rating as
  metadata to each chunk — this fixes the "he's great — who?" context problem and gives
  us free source attribution.

### Reddit threads (sources 8, 10)

- **Chunk size:** the original post is split into ~400-token chunks; each top-level
  comment is its own chunk (~30–200 tokens).
- **Overlap:** ~60 tokens (~15%) on the post body only; 0 between comments.
- **Reasoning:** A thread is a hybrid. The opening post is article-like — one point can
  span several sentences — so it gets fixed-size chunks with overlap so an idea isn't
  severed at a boundary. The comments are review-like (independent answers from
  different students), so we keep each comment whole and separate, like a review. We
  attach the thread title as metadata so a retrieved comment still has context.

### Articles / long-form (source 9, "Why CS at Tufts")

- **Chunk size:** ~400 tokens (~1,600 characters).
- **Overlap:** ~60 tokens (~15%).
- **Reasoning:** This is continuous prose where a single idea is developed across a
  paragraph. ~400 tokens keeps roughly a paragraph or two intact — large enough not to
  fragment an argument, small enough not to bury the relevant sentence in noise. The
  15% overlap carries a sentence or two across each boundary so a point split
  mid-paragraph still appears whole in at least one chunk. We split on natural
  boundaries first (paragraph → sentence → hard cut) using a recursive splitter rather
  than blind character counting.

### Summary

| Source type | Chunk size | Overlap | Split on |
|---|---|---|---|
| RMP reviews (1–7) | 1 review (~30–120 tok) | 0 | review boundary |
| Reddit (8, 10) | post ~400 tok / per comment | 15% post, 0 comments | comment boundary |
| Article (9) | ~400 tok (~1,600 char) | ~60 tok (15%) | paragraph → sentence |

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers`. It runs locally
(no API cost, no rate limits), is fast, and produces 384-dimension vectors that are
plenty for a corpus this small. Its 256-token input limit is a fine match for our
chunks — reviews are well under that, and our ~400-token article chunks are split
small enough to fit. We store the vectors in ChromaDB, which uses cosine similarity for
search.

**Top-k:** Retrieve **k = 5** chunks per query. Because review chunks are tiny, a single
chunk rarely holds a full answer — opinion questions ("is Ming Chow an easy A?") need
*several* student voices to be trustworthy, so we need k > 1–2. But too high (k = 20)
drags in loosely-related chunks that dilute the prompt and can pull the LLM off-topic or
let it cite a weakly-relevant source. k = 5 balances enough corroborating context
against keeping the prompt focused; we'll tune it during evaluation if retrieval misses.

**Why semantic search works without shared words:** The embedding model maps text to
vectors by *meaning*, not exact tokens. "Is the workload heavy?" lands near a review
that says "this class ate my whole weekend" even though they share no keywords, because
the model learned those phrases express the same concept. This is the key advantage
over keyword search for opinion text, where students phrase the same complaint a dozen
different ways.

**Production tradeoff reflection:** If this were deployed for real users and cost
weren't a constraint, I'd weigh:
- **Accuracy on domain text** — a larger model (e.g. OpenAI `text-embedding-3-large` or
  Cohere `embed-v3`) retrieves more accurately on nuanced, sarcastic student opinions
  where MiniLM can miss. Worth it if eval shows retrieval misses.
- **Context length** — MiniLM truncates at 256 tokens. An API model with an 8k window
  could embed whole long reviews or full articles without aggressive chunking, reducing
  information split across boundaries.
- **Local vs. API** — local (MiniLM) means zero per-query cost, privacy, and offline
  use, but lower ceiling on quality. API means better embeddings but ongoing cost,
  latency per call, and a rate-limited dependency.
- **Multilingual** — not a real need here (this corpus is English-only), so I would
  *not* pay for a multilingual model; that's a case where the "better" model is wasted
  budget for this domain.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | Is Ming Chow's class considered an easy A? | Yes. Reviews describe it as low-stress and "the perfect balance" — teaches a few useful things while still being an easy A. (Source: RMP Ming Chow, #3) |
| 2 | Which CS professor do students rate most highly, and why? | Milod Kazerounian — reviews call him "the best CS professor at Tufts": caring, understanding, accommodating, with engaging lectures and humor. (Source: RMP Kazerounian, #1) |
| 3 | How time-consuming is Mark Sheldon's class? | Very. Students say he is passionate and knowledgeable, but the class is "super time consuming" and requires "a LOT of time." (Source: RMP Mark Sheldon, #2) |
| 4 | Do engineering students get priority course registration over arts & sciences CS students? | Yes. A r/Tufts commenter explains engineering students register ahead of A&S CS students, so classes fill up and A&S students get shut out and have to take CS courses later (often senior year). (Source: Reddit "Science vs Engineering") |
| 5 | Why does the Tufts CS curriculum start with C++ instead of Java or Python? | Because C++ is lower-level and teaches how memory works plus abstraction and modularity, so later languages are easier to appreciate; this is reinforced by CS40, taught in C. (Source: "Why CS at Tufts" article) |

These 5 questions deliberately cover all three source types — RMP reviews (Q1–3), a
Reddit thread (Q4), and the article (Q5) — so evaluation exercises the whole corpus,
not just one source.

**Note on expected answers:** these are drawn from the actual ingested text and were
confirmed by retrieval testing — each question's correct source chunk is retrieved at
rank #1.

**Documented failure case (found during retrieval testing):** "Can you resubmit
assignments in David Lillethun's class?" The answer exists almost verbatim in the corpus
("All assignments can be resubmitted if it was not correct the first time"), but that
chunk ranks #22 of 44 (distance 0.707) and never reaches the top-5 — even when the query
is reworded to match the chunk's own wording. Root cause: **embedding dilution at the
chunking stage** — our "1 review = 1 chunk" rule keeps the review whole, but it is mostly
*about* boring lectures / OS topics, so the one resubmission clause is averaged out of the
chunk embedding. This is a retrieval failure, not a wording failure (4 rephrasings all
failed). A fix would require sentence-level chunking, which trades away the context that
keeping whole reviews provides.

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->
ingestion pipeline needs to tag each document with its source_type

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

I'll use **Claude Code** as my main coding assistant throughout, giving it the relevant
section of this planning.md as the spec for each stage. The plan per stage:

**1. Ingestion (`ingest.py`)**
- Tool: Claude Code.
- Input: my Documents table (the 10 URLs) + the note that each doc must be tagged with
  `source_type` (`rmp` / `reddit` / `article`).
- Expected output: a `load_and_clean()` function using requests + beautifulsoup4 that
  fetches each URL, strips nav/ads/boilerplate, and writes cleaned text + metadata
  (source_type, professor/course name, url) to `data/raw/`.
- Verify: run it on all 10 sources and manually open 2–3 files in `data/raw/` to confirm
  the text is clean (no nav junk) and the metadata is correct.

**2. Chunking (`chunk.py`)**
- Tool: Claude Code.
- Input: my Chunking Strategy section (the per-source-type table).
- Expected output: a `chunk_document()` that routes by `source_type` — 1 chunk per
  review (no overlap), ~400-token/15%-overlap recursive splitting for articles, the
  hybrid rule for Reddit — using langchain-text-splitters, preserving metadata on each
  chunk.
- Verify: print chunk counts and lengths; confirm reviews are 1-per-chunk and article
  chunks land near 400 tokens with visible overlap. Spot-check that no review is split.

**3. Embed + Store (`embed_store.py`)**
- Tool: Claude Code.
- Input: my Retrieval Approach section (model = all-MiniLM-L6-v2, store = ChromaDB).
- Expected output: code that embeds all chunks with sentence-transformers and persists
  them to a ChromaDB collection in `data/chroma/`, keeping metadata.
- Verify: confirm the collection count equals my total chunk count; run one test query
  and check it returns results with non-zero similarity.

**4. Retrieval (`retrieve.py`)**
- Tool: Claude Code.
- Input: Retrieval Approach section (top-k = 5).
- Expected output: a `retrieve(query, k=5)` that embeds the query and returns the top-5
  chunks with their text, metadata, and similarity scores.
- Verify: run my 5 eval questions through it **before** adding generation, and read the
  retrieved chunks by hand — this catches retrieval failures early (the project hint).

**5. Generation (`generate.py`)**
- Tool: Claude Code to write it; the runtime LLM is Ollama (llama3.1) locally.
- Input: a grounding requirement — answer **only** from retrieved chunks, cite sources,
  say "I don't know" if the chunks don't support an answer.
- Expected output: `answer(query)` that retrieves, builds a grounded prompt, calls the
  LLM, and returns the answer plus a list of cited sources.
- Verify: run the 5 eval questions; confirm every answer cites real sources and that Q5
  (the planted failure) ideally triggers an "I don't know" rather than a hallucination.

**Interface + Evaluation (`app.py`, `evaluate.py`)**
- Tool: Claude Code.
- Input: the Evaluation Plan table.
- Expected output: a Streamlit UI for live demo, and `evaluate.py` that runs all 5
  questions and prints question / retrieved chunks / answer / accuracy verdict.
- Verify: the eval output matches the format my Evaluation Report needs, and the demo
  runs end-to-end without me explaining how to navigate it.

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
