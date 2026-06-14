"""
Stage 4 of the pipeline: RETRIEVAL.

Given a user query string, embed it with the same model used to build the store,
run a cosine similarity search against the persisted ChromaDB collection, and
return the top-k chunks together with their source metadata and distance scores.

This is the QUERY half of the pipeline — it does NOT rebuild anything. Run
embed_store.py first to populate chroma_db/.

The model is loaded once at import time (not per query) so repeated calls are fast.

Run:  python3 retrieve.py        # tests retrieval on the eval-plan questions
"""

import chromadb
from chromadb.errors import NotFoundError
from sentence_transformers import SentenceTransformer

from config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL, N_RESULTS

# Load once and reuse across queries.
_model = SentenceTransformer(EMBEDDING_MODEL)
_client = chromadb.PersistentClient(path=CHROMA_PATH)


def _get_collection():
    """Fetch the collection handle. Rebuilding the store (embed_store.py) deletes
    and recreates the collection with a new internal id, which invalidates any
    cached handle — so we always re-fetch by name rather than caching it."""
    return _client.get_collection(CHROMA_COLLECTION)


def retrieve(query, k=N_RESULTS):
    """Return the top-k chunks for a query.

    Returns a list of dicts (best match first), each with:
      - "text"        : the chunk text (str)
      - "name"        : source document name, for attribution (str)
      - "url"         : source URL, for attribution (str)
      - "source_type" : "rmp" | "reddit" | "article" (str)
      - "position"    : chunk position within its document (int)
      - "distance"    : cosine distance, 0 = identical, higher = less similar (float)
    """
    embedding = _model.encode([query]).tolist()
    try:
        res = _get_collection().query(query_embeddings=embedding, n_results=k)
    except NotFoundError:
        raise SystemExit(
            "Vector store collection not found. Run `python3 embed_store.py` first "
            "to build it."
        )

    results = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        results.append({
            "text": doc,
            "name": meta["name"],
            "url": meta["url"],
            "source_type": meta["source_type"],
            "position": meta["position"],
            "distance": dist,
        })
    return results


def _print_results(query, results):
    """Pretty-print retrieval results for manual inspection / debugging."""
    print("\n" + "=" * 78)
    print(f"QUERY: {query}")
    print("=" * 78)
    for rank, r in enumerate(results, 1):
        flag = "  <-- weak match (>0.6)" if r["distance"] > 0.6 else ""
        print(f"\n[{rank}] distance={r['distance']:.3f}{flag}")
        print(f"    source: {r['name']}  (pos {r['position']})")
        text = " ".join(r["text"].split())          # collapse newlines for readability
        print(f"    text  : {text[:320]}{'...' if len(text) > 320 else ''}")


# The 5 evaluation-plan questions from planning.md.
# Chosen to cover all three source types: RMP reviews (1-3), a Reddit thread (4),
# and the article (5). The "resubmit in Lillethun's class" question is NOT in this
# set — retrieval testing showed it is a genuine dilution failure, documented
# separately as the Failure Case in the README.
EVAL_QUESTIONS = [
    "Is Ming Chow's class considered an easy A?",
    "Which CS professor do students rate most highly, and why?",
    "How time-consuming is Mark Sheldon's class?",
    "Do engineering students get priority course registration over arts & sciences CS students?",
    "Why does the Tufts CS curriculum start with C++ instead of Java or Python?",
]


if __name__ == "__main__":
    for q in EVAL_QUESTIONS:
        _print_results(q, retrieve(q))
