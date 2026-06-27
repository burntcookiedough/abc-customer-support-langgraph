# Documentation Report

## Task 1: LangGraph Workflow

The workflow begins by loading customer memory, classifies the query, routes the query to the required department, retrieves document context for support agents, applies human approval for high-risk requests, validates the answer through a supervisor, and stores the final interaction in SQLite memory.

## Task 2: State Structure

The `SupportState` structure manages:

- `customer_id`
- `query`
- `intent`
- `routed_department`
- `retrieved_context`
- `conversation_history`
- `high_risk`
- `approval_required`
- `approval_status`
- `draft_response`
- `final_response`
- `trace`

## Task 3: Intent Classification

The classifier uses deterministic keyword matching to assign customer queries to Sales, Technical Support, Billing, Account, or Memory Recall. Memory recall is detected before department scoring.

## Task 4: Conditional Routing

LangGraph conditional edges route classified queries to the matching support agent. Memory recall bypasses department routing and answers from SQLite memory.

## Task 5: Specialized Agents

The system implements Sales, Technical Support, Billing, and Account nodes. Each agent uses the retrieved company context and creates a department-specific draft answer.

## Task 6: RAG Pipeline

The local RAG pipeline reads the four company documents from `data/`, tokenizes each document and query, scores overlap, and returns the highest-ranking relevant documents.

## Task 7: SQLite Memory

The `SQLiteMemory` class creates a `conversations` table and stores customer ID, query, intent, response, and timestamp. The memory recall query retrieves the most recent previous issue for the same customer.

## Task 8: Human-in-the-Loop

Refund requests, subscription cancellation, account closure, compensation, and escalation to management are marked as high-risk. These requests route to `human_approval` before supervisor validation. The demo simulates supervisor approval with `approved_for_demo`.

## Task 9: Supervisor Agent

The supervisor validates the draft response, checks high-risk approval status, and produces the final customer-facing response.

## Task 10: Demonstration

The `src/run_demo.py` script runs all five required queries and writes the output to `artifacts/demo_output.txt`.

