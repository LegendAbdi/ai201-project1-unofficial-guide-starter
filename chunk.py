"""
Stage 2 of the pipeline: CHUNKING.

Splits each loaded document (from ingest.py) into chunks ready for embedding.
We do NOT use one uniform chunk size — chunking is routed by source_type, per
the Chunking Strategy in planning.md:

  - rmp / reddit : segments are separated by a hard delimiter line ("----").
                   Each segment (one review, or one Reddit post/comment) becomes
                   one chunk with NO overlap, because each is a complete, self-
                   contained opinion and must not be merged with another.
  - article      : continuous prose with no delimiters, so we use a paragraph-
                   based sliding window of ~1600 characters with ~240 (15%)
                   overlap so an idea split mid-paragraph still survives intact.

Safety net: if a delimited segment is itself longer than ARTICLE_CHUNK_SIZE
(e.g. a very long Reddit post), it is sub-split with the same windowing so no
single chunk is unbounded.

Each chunk is a dict:
  - "text"        : the chunk text (str)
  - "source_type" : "rmp" | "reddit" | "article" (str)
  - "name"        : source label, for citations (str)
  - "url"         : source URL, for citations (str)
  - "chunk_id"    : unique id, e.g. "rmp_chow_0" (str)
"""

import re

from ingest import load_documents

# --- Article / long-segment windowing (characters) ---
ARTICLE_CHUNK_SIZE = 1600   # ~400 tokens
ARTICLE_OVERLAP = 240       # ~15% of chunk size
MIN_LENGTH = 40             # drop whitespace-only / trivial fragments

# A delimiter line is 4+ dashes on its own line (allows surrounding whitespace).
DELIM_RE = re.compile(r"^\s*-{4,}\s*$", re.MULTILINE)


def _slug(name):
    """Make a filesystem/id-friendly prefix from a source name."""
    s = name.lower()
    s = re.sub(r"\(.*?\)", "", s)          # drop "(RMP)" etc.
    s = re.sub(r"[^a-z0-9]+", "_", s)      # non-alnum -> underscore
    return s.strip("_")


def _window(text, size=ARTICLE_CHUNK_SIZE, overlap=ARTICLE_OVERLAP):
    """Sliding-window split of long text, preferring to break on a paragraph
    or sentence boundary near the window edge rather than mid-word."""
    text = text.strip()
    if len(text) <= size:
        return [text] if len(text) >= MIN_LENGTH else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            # try to end on a paragraph break, then a sentence, near the edge
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "))
            if cut > size // 2:            # only honor a "nice" break past halfway
                end = start + cut + 1
        piece = text[start:end].strip()
        if len(piece) >= MIN_LENGTH:
            chunks.append(piece)
        if end >= len(text):
            break
        start = end - overlap              # step back to create overlap
    return chunks


def _segments(text):
    """Split a document into hard segments on '----' delimiter lines."""
    return [s.strip() for s in DELIM_RE.split(text) if s.strip()]


def chunk_document(doc):
    """Chunk one document dict (from load_documents) into a list of chunk dicts."""
    prefix = _slug(doc["name"])
    pieces = []

    if doc["source_type"] in ("rmp", "reddit"):
        # Hard boundaries: each delimited segment is its own unit.
        for seg in _segments(doc["text"]):
            # Safety net: sub-split a segment only if it's too long to be one chunk.
            pieces.extend(_window(seg) if len(seg) > ARTICLE_CHUNK_SIZE else [seg])
    else:  # "article" — continuous prose, no delimiters
        pieces.extend(_window(doc["text"]))

    chunks = []
    for i, text in enumerate(pieces):
        if len(text) < MIN_LENGTH:
            continue
        chunks.append({
            "text": text,
            "source_type": doc["source_type"],
            "name": doc["name"],
            "url": doc["url"],
            "position": i,                 # this chunk's index within its document
            "chunk_id": f"{prefix}_{i}",
        })
    return chunks


def chunk_all():
    """Load every document and chunk it. Returns a flat list of chunk dicts."""
    documents = load_documents()
    all_chunks = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))
    print(f"Produced {len(all_chunks)} chunk(s) from {len(documents)} document(s).")
    return all_chunks


if __name__ == "__main__":
    chunks = chunk_all()
    print("-" * 70)
    # Per-source summary
    by_src = {}
    for c in chunks:
        by_src.setdefault(c["name"], []).append(len(c["text"]))
    for name, lens in by_src.items():
        print(f"  {name:<48} {len(lens):>2} chunks  (avg {sum(lens)//len(lens)} chars)")
    print("-" * 70)
    # Show a couple of sample chunks so you can eyeball boundaries
    print("SAMPLE chunk (first):\n", chunks[0]["text"][:300], "\n")
    print("SAMPLE chunk (an article chunk):")
    art = next((c for c in chunks if c["source_type"] == "article"), None)
    if art:
        print(" ", art["text"][:300])
