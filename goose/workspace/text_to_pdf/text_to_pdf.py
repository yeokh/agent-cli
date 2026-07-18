#!/usr/bin/env python3
import argparse
import pathlib
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


def wrap_text(text: str, c: canvas.Canvas, font_name: str, font_size: float, max_width: float):
    """Wrap text into lines that fit max_width (points)."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    cur = words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def text_file_to_pdf(input_path: pathlib.Path, output_path: pathlib.Path, title: str | None = None):
    page_w, page_h = A4
    margin_l = 15 * mm
    margin_r = 15 * mm
    margin_t = 15 * mm
    margin_b = 15 * mm
    line_gap = 1.2
    font_name = "Helvetica"
    font_size = 10
    leading = font_size * line_gap

    c = canvas.Canvas(str(output_path), pagesize=A4)
    c.setTitle(title or output_path.stem)

    usable_w = page_w - margin_l - margin_r
    max_lines = int((page_h - margin_t - margin_b) / leading)

    y = page_h - margin_t

    if title:
        c.setFont(font_name, 14)
        c.drawString(margin_l, y, title)
        y -= 18
        c.setFont(font_name, font_size)

    with input_path.open("r", encoding="utf-8") as f:
        raw = f.read()

    paragraphs = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n\n")

    for pi, p in enumerate(paragraphs):
        if p.strip() == "":
            # Paragraph break
            y -= leading
            continue

        # Keep internal newlines: treat them as soft paragraph line breaks
        p = p.replace("\n", " ").strip()
        lines = wrap_text(p, c, font_name, font_size, usable_w)

        for line in lines:
            if y - leading < margin_b:
                c.showPage()
                c.setFont(font_name, font_size)
                y = page_h - margin_t
            c.drawString(margin_l, y, line)
            y -= leading

        # Paragraph spacing
        y -= leading * 0.5

    c.save()


def main():
    ap = argparse.ArgumentParser(description="Convert a text file to a PDF.")
    ap.add_argument("input", type=pathlib.Path, help="Input .txt file")
    ap.add_argument("output", type=pathlib.Path, help="Output .pdf file")
    ap.add_argument("--title", type=str, default=None, help="Optional PDF title")
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    if args.output.suffix.lower() != ".pdf":
        raise SystemExit("Output must end with .pdf")

    text_file_to_pdf(args.input, args.output, title=args.title or None)


if __name__ == "__main__":
    main()
