from __future__ import annotations

import sqlite3
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def draw_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], text: str, fill: str) -> None:
    draw.rounded_rectangle(xy, radius=8, fill=fill, outline="#1f2937", width=2)
    x1, y1, x2, y2 = xy
    lines = textwrap.wrap(text, width=24)
    line_height = 24
    total_height = len(lines) * line_height
    y = y1 + ((y2 - y1) - total_height) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font(18))
        draw.text((x1 + ((x2 - x1) - (bbox[2] - bbox[0])) // 2, y), line, fill="#111827", font=font(18))
        y += line_height


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line([start, end], fill="#111827", width=3)
    x, y = end
    draw.polygon([(x, y), (x - 10, y - 6), (x - 10, y + 6)], fill="#111827")


def make_workflow_diagram() -> None:
    image = Image.new("RGB", (1500, 920), "#f8fafc")
    draw = ImageDraw.Draw(image)
    draw.text((50, 35), "ABC Technologies LangGraph Customer Support Workflow", fill="#111827", font=font(32))

    boxes = {
        "Customer Query": (80, 120, 330, 200),
        "Load SQLite Memory": (430, 120, 680, 200),
        "Intent Classification": (780, 120, 1030, 200),
        "Memory Recall Agent": (1130, 40, 1380, 120),
        "RAG Retrieval": (1130, 200, 1380, 280),
        "Sales Agent": (180, 390, 390, 470),
        "Technical Agent": (470, 390, 680, 470),
        "Billing Agent": (760, 390, 970, 470),
        "Account Agent": (1050, 390, 1260, 470),
        "Human Approval": (760, 570, 970, 650),
        "Supervisor Agent": (560, 720, 810, 800),
        "Save Memory": (910, 720, 1160, 800),
        "Final Response": (1210, 720, 1430, 800),
    }

    fills = {
        "Customer Query": "#dbeafe",
        "Load SQLite Memory": "#dcfce7",
        "Intent Classification": "#fef3c7",
        "Memory Recall Agent": "#e0e7ff",
        "RAG Retrieval": "#e0f2fe",
        "Human Approval": "#fee2e2",
        "Supervisor Agent": "#ede9fe",
        "Save Memory": "#dcfce7",
        "Final Response": "#d1fae5",
    }

    for label, xy in boxes.items():
        draw_box(draw, xy, label, fills.get(label, "#ffffff"))

    draw_arrow(draw, (330, 160), (430, 160))
    draw_arrow(draw, (680, 160), (780, 160))
    draw_arrow(draw, (1030, 160), (1130, 80))
    draw_arrow(draw, (1030, 185), (1130, 240))
    for x in [285, 575, 865, 1155]:
        draw.line([(1255, 280), (1255, 330), (x, 330), (x, 390)], fill="#111827", width=3)
    draw_arrow(draw, (865, 470), (865, 570))
    draw.text((982, 585), "high-risk only", fill="#7f1d1d", font=font(16))
    for start in [(285, 470), (575, 470), (1155, 470), (865, 650), (1255, 120)]:
        draw_arrow(draw, start, (685, 720))
    draw_arrow(draw, (810, 760), (910, 760))
    draw_arrow(draw, (1160, 760), (1210, 760))

    image.save(ARTIFACTS / "workflow_diagram.png")


def make_schema_file() -> None:
    schema = """
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    query TEXT NOT NULL,
    intent TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""".strip()
    (ARTIFACTS / "memory_schema.sql").write_text(schema + "\n", encoding="utf-8")


def make_screenshots_pdf() -> None:
    output = (ARTIFACTS / "demo_output.txt").read_text(encoding="utf-8")
    sections = [section.strip() for section in output.split("\n\n") if section.strip()]
    pages: list[Image.Image] = []
    for idx, section in enumerate(sections, start=1):
        image = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(image)
        draw.text((70, 60), f"Task Output Screenshot {idx}", fill="#111827", font=font(34))
        y = 125
        for line in section.splitlines():
            wrapped = textwrap.wrap(line, width=100) or [""]
            for part in wrapped:
                draw.text((70, y), part, fill="#111827", font=font(22))
                y += 32
            if y > 1650:
                break
        pages.append(image)
    pages[0].save(ARTIFACTS / "screenshots.pdf", save_all=True, append_images=pages[1:])


def verify_db() -> None:
    db_path = ARTIFACTS / "memory.db"
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    if count < 5:
        raise RuntimeError(f"Expected at least five stored conversations, found {count}")


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    verify_db()
    make_workflow_diagram()
    make_schema_file()
    make_screenshots_pdf()


if __name__ == "__main__":
    main()
