"""Build a simple text-based PDF of the executive report (stdlib only)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD = ROOT / "docs" / "executive_report.md"
OUT = ROOT / "docs" / "executive_report.pdf"


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def md_to_pdf(md_path: Path, pdf_path: Path) -> None:
    """Minimal multi-page PDF writer (Helvetica, wrapped lines)."""
    text = md_path.read_text(encoding="utf-8")
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            line = line.lstrip("#").strip().upper()
        elif line.startswith("|") or line.startswith("```") or line.startswith("-"):
            line = line.replace("|", " ").strip()
        # wrap ~90 chars
        while len(line) > 90:
            cut = line.rfind(" ", 0, 90)
            if cut < 40:
                cut = 90
            lines.append(line[:cut])
            line = line[cut:].lstrip()
        lines.append(line)

    # paginate ~48 lines / page
    pages: list[list[str]] = []
    for i in range(0, len(lines), 48):
        pages.append(lines[i : i + 48])
    if not pages:
        pages = [[""]]

    objs: list[bytes] = []
    # 1 catalog, 2 pages tree, then per page: page + content

    def add(obj: bytes) -> int:
        objs.append(obj)
        return len(objs)

    content_ids: list[int] = []
    page_ids: list[int] = []

    # We'll build content streams first as placeholders by constructing in order:
    # Actually build all content, then pages, then pages tree, then catalog — rewrite with two passes.
    content_streams: list[bytes] = []
    for page_lines in pages:
        y = 800
        parts = ["BT /F1 10 Tf 50 800 Td 12 TL"]
        first = True
        for ln in page_lines:
            esc = _escape(ln)
            if first:
                parts.append(f"({esc}) Tj")
                first = False
            else:
                parts.append(f"T* ({esc}) Tj")
        parts.append("ET")
        stream = "\n".join(parts).encode("latin-1", errors="replace")
        content_streams.append(stream)

    # Object layout:
    # 1: Catalog
    # 2: Pages
    # 3: Font
    # then pairs (Page, Content) for each page
    font_id = 3
    page_obj_ids = []
    content_obj_ids = []
    next_id = 4
    for _ in content_streams:
        page_obj_ids.append(next_id)
        content_obj_ids.append(next_id + 1)
        next_id += 2

    out_objs: dict[int, bytes] = {}
    kids = " ".join(f"{i} 0 R" for i in page_obj_ids)
    out_objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    out_objs[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_ids)} >>".encode()
    out_objs[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    for pid, cid, stream in zip(page_obj_ids, content_obj_ids, content_streams):
        out_objs[pid] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {cid} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        ).encode()
        out_objs[cid] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    # Write PDF
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with pdf_path.open("wb") as f:
        f.write(b"%PDF-1.4\n")
        offsets = {0: 0}
        max_id = max(out_objs)
        for i in range(1, max_id + 1):
            offsets[i] = f.tell()
            f.write(f"{i} 0 obj\n".encode())
            f.write(out_objs[i])
            f.write(b"\nendobj\n")
        xref = f.tell()
        f.write(f"xref\n0 {max_id + 1}\n".encode())
        f.write(b"0000000000 65535 f \n")
        for i in range(1, max_id + 1):
            f.write(f"{offsets[i]:010d} 00000 n \n".encode())
        f.write(
            f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        )


if __name__ == "__main__":
    md_to_pdf(MD, OUT)
    print(f"wrote {OUT}")
