# AI-Powered Customer Support Automation System

This project implements a LangGraph-based customer support automation workflow for ABC Technologies.

## Features

- Accepts customer support queries.
- Classifies issue type into Sales, Technical Support, Billing, Account, or Memory Recall.
- Routes each query to the correct specialized support agent.
- Retrieves relevant context from company documents using a lightweight local RAG pipeline.
- Stores and retrieves customer conversation history with SQLite.
- Requires human approval for high-risk requests such as refunds, cancellations, account closure, compensation, and escalation to management.
- Uses a supervisor node to validate and improve the final response.

## Project Structure

```text
src/
  support_system.py      Main LangGraph workflow and nodes
  run_demo.py            Runs the five required sample queries
data/
  company_policy.txt
  pricing_guide.txt
  technical_manual.txt
  faq.txt
docs/
  documentation_report.md
artifacts/
  workflow_diagram.png
  screenshots.pdf
  demo_output.txt
  memory.db
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python src/run_demo.py
```

The demo creates `artifacts/memory.db` and writes execution output to `artifacts/demo_output.txt`.

## Required Demonstration Queries

1. What are the pricing plans available for your software?
2. I forgot my account password.
3. My application crashes whenever I upload a file.
4. I need a refund for my annual subscription.
5. What was my previous support issue?

