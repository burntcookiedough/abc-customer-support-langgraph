CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    query TEXT NOT NULL,
    intent TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
