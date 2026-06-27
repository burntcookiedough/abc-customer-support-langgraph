from __future__ import annotations

from pathlib import Path

from support_system import CustomerSupportGraph


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
DOCS = ROOT / "data"
DB_PATH = ARTIFACTS / "memory.db"


DEMO_QUERIES = [
    "What are the pricing plans available for your software?",
    "I forgot my account password.",
    "My application crashes whenever I upload a file.",
    "I need a refund for my annual subscription.",
    "What was my previous support issue?",
]


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    app = CustomerSupportGraph(docs_dir=DOCS, db_path=DB_PATH)
    lines: list[str] = []

    for index, query in enumerate(DEMO_QUERIES, start=1):
        result = app.invoke(customer_id="customer_david", query=query)
        lines.extend(
            [
                f"Query {index}: {query}",
                f"Intent / Route: {result['intent']}",
                f"Approval required: {result.get('approval_required', False)}",
                f"Approval status: {result.get('approval_status', 'not_required')}",
                "Trace:",
                *[f"  - {item}" for item in result.get("trace", [])],
                "Retrieved context:",
                *[f"  - {item.splitlines()[0]}" for item in result.get("retrieved_context", [])],
                f"Final response: {result['final_response']}",
                "",
            ]
        )

    output = "\n".join(lines)
    (ARTIFACTS / "demo_output.txt").write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
