"""
Two-layer guardrails for the NL → SQL query pipeline.

Layer 1 — Keyword filter: blocks SQL injection attempts and off-topic questions
           before they ever reach the LLM.
Layer 2 — System prompt enforcement: the LLM is instructed to reject non-O2C
           questions itself (handled in llm.py).
"""

BLOCKED_KEYWORDS: list[str] = [
    "drop table", "drop database", "truncate", "delete from", "alter table",
    "create table", "insert into", "update ", "grant ", "revoke ",
    "exec ", "execute ", "xp_", "sys.", "information_schema",
    "pg_catalog", "pg_sleep", "--", "/*", "*/", ";--",
    "union select", "or 1=1", "' or '", "benchmark(",
]

OFF_TOPIC_KEYWORDS: list[str] = [
    "weather", "stock price", "sports", "movie", "recipe",
    "politics", "celebrity", "joke", "poem", "song",
]

REJECTION_MSG = "This system only answers questions about the Order-to-Cash dataset."


def check_input_guardrail(user_message: str) -> str | None:
    """
    Layer 1: keyword-based pre-filter.

    Returns a rejection message if the input is blocked, otherwise ``None``.
    """
    lower = user_message.lower().strip()

    for keyword in BLOCKED_KEYWORDS:
        if keyword in lower:
            return (
                "Your query contains disallowed SQL keywords. "
                "Please rephrase your question in natural language."
            )

    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in lower:
            return REJECTION_MSG

    return None
