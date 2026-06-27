from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

try:
    from langgraph.graph import END, StateGraph
except Exception as exc:  # pragma: no cover
    raise RuntimeError("LangGraph is required. Install dependencies with: pip install -r requirements.txt") from exc


Department = Literal["Sales", "Technical Support", "Billing", "Account", "Memory Recall"]

HIGH_RISK_PATTERNS = [
    "refund",
    "cancel",
    "cancellation",
    "close account",
    "account closure",
    "delete my account",
    "compensation",
    "escalate",
    "management",
]

DEPARTMENT_KEYWORDS = {
    "Sales": ["pricing", "plans", "subscription plan", "price", "product information", "features"],
    "Technical Support": ["crash", "error", "install", "installation", "login", "configuration", "upload", "bug"],
    "Billing": ["invoice", "payment", "billing", "refund", "charge", "annual subscription"],
    "Account": ["password", "profile", "account activation", "deactivation", "activate", "reset"],
}


class SupportState(TypedDict, total=False):
    customer_id: str
    query: str
    intent: Department
    routed_department: str
    retrieved_context: list[str]
    conversation_history: list[str]
    high_risk: bool
    approval_required: bool
    approval_status: str
    draft_response: str
    final_response: str
    trace: list[str]


@dataclass
class RetrievedDocument:
    source: str
    text: str
    score: int


class SQLiteMemory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add(self, customer_id: str, query: str, intent: str, response: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (customer_id, query, intent, response) VALUES (?, ?, ?, ?)",
                (customer_id, query, intent, response),
            )

    def history(self, customer_id: str, limit: int = 5) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT query, intent, response
                FROM conversations
                WHERE customer_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (customer_id, limit),
            ).fetchall()
        return [f"Query: {query} | Issue: {intent} | Response: {response}" for query, intent, response in rows]

    def previous_issue(self, customer_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT query, intent
                FROM conversations
                WHERE customer_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (customer_id,),
            ).fetchone()
        if not row:
            return None
        return f"Your previous support issue was classified as {row[1]}: {row[0]}"


class LocalRAG:
    def __init__(self, docs_dir: Path) -> None:
        self.documents = []
        for path in sorted(docs_dir.glob("*.txt")):
            self.documents.append((path.name, path.read_text(encoding="utf-8")))

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z]{3,}", text.lower()))

    def retrieve(self, query: str, intent: str, limit: int = 2) -> list[RetrievedDocument]:
        query_tokens = self._tokens(f"{query} {intent}")
        ranked: list[RetrievedDocument] = []
        for source, text in self.documents:
            score = len(query_tokens & self._tokens(text))
            if intent.lower().split()[0] in source.replace("_", " "):
                score += 3
            ranked.append(RetrievedDocument(source=source, text=text.strip(), score=score))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return [item for item in ranked[:limit] if item.score > 0]


class CustomerSupportGraph:
    def __init__(self, docs_dir: Path, db_path: Path) -> None:
        self.memory = SQLiteMemory(db_path)
        self.rag = LocalRAG(docs_dir)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(SupportState)
        workflow.add_node("load_memory", self.load_memory)
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("retrieve_context", self.retrieve_context)
        workflow.add_node("sales_agent", self.sales_agent)
        workflow.add_node("technical_agent", self.technical_agent)
        workflow.add_node("billing_agent", self.billing_agent)
        workflow.add_node("account_agent", self.account_agent)
        workflow.add_node("memory_agent", self.memory_agent)
        workflow.add_node("human_approval", self.human_approval)
        workflow.add_node("supervisor", self.supervisor)
        workflow.add_node("save_memory", self.save_memory)

        workflow.set_entry_point("load_memory")
        workflow.add_edge("load_memory", "classify_intent")
        workflow.add_conditional_edges(
            "classify_intent",
            self.route_after_classification,
            {
                "Sales": "retrieve_context",
                "Technical Support": "retrieve_context",
                "Billing": "retrieve_context",
                "Account": "retrieve_context",
                "Memory Recall": "memory_agent",
            },
        )
        workflow.add_conditional_edges(
            "retrieve_context",
            self.route_to_agent,
            {
                "Sales": "sales_agent",
                "Technical Support": "technical_agent",
                "Billing": "billing_agent",
                "Account": "account_agent",
            },
        )
        for node in ["sales_agent", "technical_agent", "billing_agent", "account_agent"]:
            workflow.add_conditional_edges(node, self.route_for_approval, {"approval": "human_approval", "supervisor": "supervisor"})
        workflow.add_edge("human_approval", "supervisor")
        workflow.add_edge("memory_agent", "save_memory")
        workflow.add_edge("supervisor", "save_memory")
        workflow.add_edge("save_memory", END)
        return workflow.compile()

    @staticmethod
    def _append_trace(state: SupportState, message: str) -> list[str]:
        return [*state.get("trace", []), message]

    def load_memory(self, state: SupportState) -> SupportState:
        history = self.memory.history(state["customer_id"])
        return {**state, "conversation_history": history, "trace": self._append_trace(state, "Loaded SQLite conversation memory")}

    def classify_intent(self, state: SupportState) -> SupportState:
        query = state["query"].lower()
        if any(phrase in query for phrase in ["previous issue", "last issue", "what was my previous"]):
            intent: Department = "Memory Recall"
        else:
            scores = {
                department: sum(1 for keyword in keywords if keyword in query)
                for department, keywords in DEPARTMENT_KEYWORDS.items()
            }
            intent = max(scores, key=scores.get)  # type: ignore[assignment]
            if scores[intent] == 0:
                intent = "Technical Support"
        high_risk = any(pattern in query for pattern in HIGH_RISK_PATTERNS)
        return {
            **state,
            "intent": intent,
            "routed_department": intent,
            "high_risk": high_risk,
            "approval_required": high_risk,
            "trace": self._append_trace(state, f"Classified intent as {intent}"),
        }

    @staticmethod
    def route_after_classification(state: SupportState) -> str:
        return state["intent"]

    def retrieve_context(self, state: SupportState) -> SupportState:
        docs = self.rag.retrieve(state["query"], state["intent"])
        snippets = [f"{doc.source}: {doc.text}" for doc in docs]
        return {**state, "retrieved_context": snippets, "trace": self._append_trace(state, "Retrieved RAG context from company documents")}

    @staticmethod
    def route_to_agent(state: SupportState) -> str:
        return state["intent"]

    @staticmethod
    def _context_summary(state: SupportState) -> str:
        context = state.get("retrieved_context", [])
        return context[0].split("\n", 1)[0] if context else "No matching company document was found."

    def sales_agent(self, state: SupportState) -> SupportState:
        response = "Sales Support: ABC Technologies offers Starter, Professional, and Enterprise plans. " + self._context_summary(state)
        return {**state, "draft_response": response, "trace": self._append_trace(state, "Sales agent drafted response")}

    def technical_agent(self, state: SupportState) -> SupportState:
        response = "Technical Support: Please check supported file type, file size, browser version, and blocking extensions. " + self._context_summary(state)
        return {**state, "draft_response": response, "trace": self._append_trace(state, "Technical Support agent drafted response")}

    def billing_agent(self, state: SupportState) -> SupportState:
        response = "Billing Support: I found that your request relates to billing or refund handling. " + self._context_summary(state)
        return {**state, "draft_response": response, "trace": self._append_trace(state, "Billing agent drafted response")}

    def account_agent(self, state: SupportState) -> SupportState:
        response = "Account Support: You can reset your password from the login page by selecting Forgot password. " + self._context_summary(state)
        return {**state, "draft_response": response, "trace": self._append_trace(state, "Account agent drafted response")}

    @staticmethod
    def route_for_approval(state: SupportState) -> str:
        return "approval" if state.get("approval_required") else "supervisor"

    def human_approval(self, state: SupportState) -> SupportState:
        approved = "approved_for_demo"
        response = state["draft_response"] + " A human supervisor has reviewed this high-risk request and approved sending this guidance."
        return {
            **state,
            "approval_status": approved,
            "draft_response": response,
            "trace": self._append_trace(state, "Human supervisor approval completed"),
        }

    def memory_agent(self, state: SupportState) -> SupportState:
        previous = self.memory.previous_issue(state["customer_id"])
        response = previous or "I do not have a previous support issue stored for you yet."
        return {
            **state,
            "draft_response": response,
            "approval_required": False,
            "approval_status": "not_required",
            "trace": self._append_trace(state, "Memory recall answered from SQLite"),
        }

    def supervisor(self, state: SupportState) -> SupportState:
        response = state["draft_response"]
        if state.get("approval_required") and not state.get("approval_status"):
            response += " This request still requires supervisor approval before final processing."
        final = response + " Thank you for contacting ABC Technologies."
        return {**state, "final_response": final, "trace": self._append_trace(state, "Supervisor validated final response")}

    def save_memory(self, state: SupportState) -> SupportState:
        final = state.get("final_response") or state.get("draft_response", "")
        self.memory.add(state["customer_id"], state["query"], state["intent"], final)
        return {**state, "final_response": final, "trace": self._append_trace(state, "Saved interaction to SQLite memory")}

    def invoke(self, customer_id: str, query: str) -> SupportState:
        return self.graph.invoke({"customer_id": customer_id, "query": query, "trace": []})
