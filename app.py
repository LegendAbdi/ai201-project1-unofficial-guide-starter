"""
Query interface for The Unofficial Guide (Stage: interface).

A minimal Gradio web UI. The user types a question; the system retrieves
relevant chunks, generates a grounded answer with generate.ask(), and shows the
answer alongside the source documents it was drawn from.

Run:  python3 app.py     then open http://localhost:7860
"""

import gradio as gr

from generate import ask

EXAMPLES = [
    "Is Ming Chow's class considered an easy A?",
    "Which CS professor do students rate most highly, and why?",
    "How time-consuming is Mark Sheldon's class?",
    "Do engineering students get priority registration over arts & sciences CS students?",
    "Why does the Tufts CS curriculum start with C++ instead of Java or Python?",
]


def handle_query(question):
    """Run one question through the RAG pipeline and format it for the UI."""
    if not question or not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"])
    if not sources:
        sources = "(no sources — the documents don't cover this question)"
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide — Tufts CS") as demo:
    gr.Markdown(
        "# The Unofficial Guide — Tufts CS\n"
        "Ask about Tufts CS professors and courses. Answers come **only** from "
        "real student reviews and r/Tufts posts — with the sources they're drawn from."
    )
    inp = gr.Textbox(
        label="Your question",
        placeholder="e.g. Is Ming Chow's class an easy A?",
    )
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
