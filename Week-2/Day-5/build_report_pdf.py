"""Build a simple 2-page PDF executive report from docs/executive_report.md content."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent / "docs" / "executive_report.pdf"


def build() -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "H2Custom",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=4,
    )
    bullet = ParagraphStyle(
        "BulletCustom",
        parent=body,
        leftIndent=12,
        spaceAfter=2,
    )

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    story = []
    story.append(Paragraph("Executive Report — Web3Geeks Client Inquiry Desk", title))
    story.append(Paragraph("Week 2 Day 5 Capstone · LangGraph + Groq + FastAPI + SQLite", body))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Business goal", h2))
    story.append(
        Paragraph(
            "Inbound client messages about price, stock, comparisons, quotes, and complaints "
            "are slow to answer by hand and easy to get wrong on numbers. This system sorts "
            "the message, looks up a local product catalog, drafts a short reply from those facts, "
            "logs the ticket, and waits for human approval before sending a quote or escalating.",
            body,
        )
    )

    story.append(Paragraph("2. Architecture", h2))
    story.append(
        Paragraph(
            "FastAPI <b>/inquire</b> and <b>/approve</b> wrap a LangGraph pipeline: "
            "validate → classify → retrieve (CSV + calculator) → draft → quality loop → "
            "human checkpoint (quote/escalate) → apply action → finalize. Failures route to "
            "a graceful error node. Tickets land in SQLite; JSONL logs capture latency, tokens, "
            "tool calls, and errors. Full diagram: docs/architecture.md.",
            body,
        )
    )

    story.append(Paragraph("3. Framework choice", h2))
    story.append(
        Paragraph(
            "LangGraph was chosen over CrewAI for this desk. The problem needs explicit control, "
            "retries, and an approval interrupt — not a free-form multi-agent chat. CrewAI helped "
            "with roles in Day 4, but hierarchical runs cost more time/tokens without a clear quality "
            "win on similar catalog work. A raw ReAct loop is fine for demos, but weaker for "
            "checkpointed approval and API resume. Catalog tools and critique ideas still reuse Days 1–4.",
            body,
        )
    )

    story.append(Paragraph("4. Evaluation results", h2))
    story.append(
        Paragraph(
            "Six criteria (0/1): task success, factual accuracy, latency, cost, tone/quality, safety. "
            "Ten test cases include empty input, prompt-injection style text, unknown products, and a "
            "simulated catalog timeout. Latest run: <b>10/10</b> task success, mean score <b>6.0/6</b>, "
            "happy-path latency about 1.5–2.5s. Full table: <b>results/evaluation_results.md</b>.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Most common failure:</b> catalog name mismatch (client wording ≠ CSV titles).",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>What to change next:</b> fuzzy/alias matching plus top-3 catalog suggestions on miss.",
            body,
        )
    )

    story.append(Paragraph("5. Known limitations", h2))
    for item in [
        "Small static CSV catalog (not live inventory).",
        "Quote send / escalate are placeholders (logged only, not real email/ITSM).",
        "MemorySaver checkpointer — open approvals do not survive process restart.",
        "Mostly keyword intent routing; odd phrasing can mis-route.",
        "Heuristic quality score, not a full judge panel.",
    ]:
        story.append(Paragraph(f"• {item}", bullet))

    story.append(Paragraph("6. Recommended next steps", h2))
    for item in [
        "Durable checkpointer (SQLite/Postgres) for HITL across deploys.",
        "Stronger guardrails + PII scrubbing in logs.",
        "Fuzzy retrieval; sync catalog from real stock DB.",
        "Simple human approval UI for the quote/escalate queue.",
        "Grow eval set; weekly regression on model changes; follow monitoring checklist.",
        "Two-week pilot in shadow mode with approval required on quotes.",
    ]:
        story.append(Paragraph(f"• {item}", bullet))

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Run: <font face='Courier'>pip install -r requirements.txt</font> · "
            "<font face='Courier'>python evaluate.py</font> · "
            "<font face='Courier'>uvicorn api:app --port 8000</font>",
            body,
        )
    )

    doc.build(story)
    print("Wrote", OUT)


if __name__ == "__main__":
    build()
