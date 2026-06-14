"""
Stage 5 of the pipeline: GROUNDED GENERATION.

Connects retrieval (Stage 4) to the Groq LLM. Given a user question:
  1. retrieve the top-k chunks,
  2. build a prompt that passes ONLY those chunks as context,
  3. instruct the model to answer from that context alone (or decline),
  4. return the answer together with a programmatically-built source list.

Grounding is enforced two ways, both intentional:
  - The SYSTEM prompt hard-requires answering only from the provided context and
    returning a fixed "I don't have enough information on that." sentence otherwise.
  - Source attribution is NOT left to the model: the "sources" returned are built
    in code from the chunks that were actually retrieved, so attribution is
    guaranteed even if the model forgets to cite.

Run:  python3 generate.py        # end-to-end test on the eval questions
"""

import re

from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL, N_RESULTS
from retrieve import retrieve

_client = Groq(api_key=GROQ_API_KEY)

NO_ANSWER = "I don't have enough information on that."

SYSTEM_PROMPT = (
    "You are an assistant that answers questions about the Tufts University "
    "Computer Science department using ONLY the context provided by the user. "
    "The context is real student reviews and forum posts.\n\n"
    "Rules you must follow:\n"
    "1. Use ONLY facts found in the CONTEXT. Never use outside or prior knowledge.\n"
    "2. If the context does not contain enough information to answer the question, "
    f'reply with EXACTLY this sentence and nothing else: "{NO_ANSWER}"\n'
    "3. Do not guess, generalize, or invent details that are not in the context.\n"
    "4. When you do answer, cite the sources you used by their [number] labels.\n"
    "5. Keep the answer concise and grounded in what students actually said."
)


def _build_context(chunks):
    """Format retrieved chunks into a numbered context block for the prompt."""
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] (source: {c['name']})\n{c['text']}")
    return "\n\n".join(blocks)


def _cited_sources(answer, chunks):
    """Build the source list from the [n] labels the model actually cited.

    Maps each cited number back to its chunk and de-duplicates by source. Falls
    back to all retrieved chunks only if the model answered but cited nothing,
    so attribution is always present. Attribution is built in code, never
    trusted to the model to format.
    """
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    used = [chunks[i - 1] for i in sorted(cited) if 1 <= i <= len(chunks)]
    if not used:                       # answered but didn't cite — show all retrieved
        used = chunks

    seen, sources = set(), []
    for c in used:
        key = (c["name"], c["url"])
        if key not in seen:
            seen.add(key)
            sources.append(f"{c['name']} — {c['url']}")
    return sources


def ask(question, k=N_RESULTS):
    """Answer a question grounded in retrieved chunks.

    Returns a dict:
      - "answer"   : the model's grounded answer (str)
      - "sources"  : de-duplicated list of "name — url" strings actually retrieved
      - "chunks"   : the raw retrieved chunks (for evaluation/debugging)
    """
    chunks = retrieve(question, k=k)

    user_prompt = (
        f"CONTEXT:\n{_build_context(chunks)}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using only the context above, following all the rules."
    )

    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        temperature=0,  # deterministic, less room to drift from context
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    answer = completion.choices[0].message.content.strip()

    # Source attribution is guaranteed in code, not trusted to the model.
    # If the model declined, we surface no sources (nothing actually supported an answer).
    sources = [] if answer == NO_ANSWER else _cited_sources(answer, chunks)

    return {"answer": answer, "sources": sources, "chunks": chunks}


if __name__ == "__main__":
    from retrieve import EVAL_QUESTIONS

    # Include one question the documents do NOT cover, to test the decline path.
    questions = EVAL_QUESTIONS + [
        "What is the meal plan like at the Tufts dining halls?",  # off-domain
    ]
    for q in questions:
        result = ask(q)
        print("\n" + "=" * 78)
        print("Q:", q)
        print("-" * 78)
        print("ANSWER:", result["answer"])
        print("SOURCES:")
        for s in result["sources"]:
            print("   •", s)
        if not result["sources"]:
            print("   (none — system declined to answer)")
