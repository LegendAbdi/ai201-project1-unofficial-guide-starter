"""
Stage 1 of the pipeline: INGESTION.

Loads each raw source file listed in sources.json, cleans it, and tags it with
its source_type + metadata (name, url). Produces a list of structured document
dicts that are ready for chunking in chunk.py.

This file does NOT chunk or embed — those are separate stages (chunk.py,
embed_store.py), so we can re-run chunking experiments without re-loading.

Why files instead of live scraping: Rate My Professors is JavaScript-rendered
and Reddit blocks automated requests, so scraping them with requests/bs4 is
unreliable. Instead, the raw text for each source is saved by hand into
documents/<file>.txt (one file per source in sources.json), and this stage
loads + cleans those files. This is recorded as a design decision in the README.
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
DOCS_PATH = BASE_DIR / "documents"
SOURCES_FILE = BASE_DIR / "sources.json"


def clean_text(text):
    """Light, source-agnostic cleanup of raw saved text.

    - normalize Windows line endings
    - strip trailing spaces on each line
    - collapse 3+ blank lines into one blank line (removes copy/paste gaps)
    Returns cleaned text, stripped of leading/trailing whitespace.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)      # trailing whitespace per line
    text = re.sub(r"\n{3,}", "\n\n", text)       # collapse big gaps
    return text.strip()


def load_documents():
    """Load + clean every source listed in sources.json.

    Returns a list of dicts, each with:
      - "id"          : the source id from sources.json (int)
      - "source_type" : "rmp" | "reddit" | "article"  (drives chunking)
      - "name"        : human-readable label, used for citations (str)
      - "url"         : original source URL, used for citations (str)
      - "text"        : the cleaned document text (str)
    Sources whose file is missing or empty are skipped with a warning, so you
    can build the corpus incrementally and re-run as you add files.
    """
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))

    documents = []
    for s in sources:
        filepath = DOCS_PATH / s["file"]

        if not filepath.exists():
            print(f"  ! missing  : {s['file']:<28} (id {s['id']}) — skipping")
            continue

        text = clean_text(filepath.read_text(encoding="utf-8"))
        if not text:
            print(f"  ! empty    : {s['file']:<28} (id {s['id']}) — skipping")
            continue

        documents.append({
            "id": s["id"],
            "source_type": s["source_type"],
            "name": s["name"],
            "url": s["url"],
            "text": text,
        })

    # Summary by source_type so you can sanity-check coverage at a glance.
    by_type = {}
    for d in documents:
        by_type[d["source_type"]] = by_type.get(d["source_type"], 0) + 1
    print(f"Loaded {len(documents)}/{len(sources)} document(s): {by_type}")
    return documents


if __name__ == "__main__":
    docs = load_documents()
    print("-" * 60)
    for d in docs:
        print(f"  [{d['source_type']:<7}] {d['name']:<45} {len(d['text']):>6} chars")
