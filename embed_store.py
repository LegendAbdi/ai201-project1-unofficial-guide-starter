"""
Stage 3 of the pipeline: EMBED + STORE.

Takes the chunks produced by chunk.py, embeds each one with the
sentence-transformers model named in config.py, and stores the vectors (plus
text + metadata) in a persistent ChromaDB collection on disk.

This is a one-time BUILD step: run it once, or whenever the documents change.
Retrieval (retrieve.py) then queries the persisted collection without re-embedding.

Run:  python3 embed_store.py        # builds/rebuilds the vector store
"""

import chromadb
from sentence_transformers import SentenceTransformer

from chunk import chunk_all
from config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL


def build_store():
    """Embed all chunks and (re)build the ChromaDB collection. Returns the collection."""
    chunks = chunk_all()
    if not chunks:
        raise SystemExit("No chunks produced — check documents/ and chunk.py first.")

    # 1. Embed the chunk texts locally with sentence-transformers.
    print(f"Embedding {len(chunks)} chunk(s) with '{EMBEDDING_MODEL}' ...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    # 2. Connect to a persistent ChromaDB on disk and start the collection fresh,
    #    so re-running always reflects the current documents (no stale duplicates).
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass  # didn't exist yet — fine
    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},  # cosine similarity, per planning.md
    )

    # 3. Store vectors + the text + citation metadata. Chroma keeps them together
    #    so retrieval returns the chunk text and its source in one call.
    collection.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "source_type": c["source_type"],
                "name": c["name"],            # source document name (for attribution)
                "url": c["url"],              # source URL (for attribution)
                "position": c["position"],    # chunk's position within its document
            }
            for c in chunks
        ],
    )

    print(f"Stored {collection.count()} chunk(s) in collection "
          f"'{CHROMA_COLLECTION}' at {CHROMA_PATH}")
    return collection


if __name__ == "__main__":
    collection = build_store()

    # Smoke test: a query should return results with non-zero similarity.
    model = SentenceTransformer(EMBEDDING_MODEL)
    q = "Which professor is the best and most caring?"
    res = collection.query(
        query_embeddings=model.encode([q]).tolist(),
        n_results=3,
    )
    print("-" * 70)
    print(f"Smoke-test query: {q!r}")
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        print(f"  [{1 - dist:.3f}] {meta['name']:<28} {doc[:70].strip()!r}")
