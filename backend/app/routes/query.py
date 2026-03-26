"""NL query and chat-history endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat import ChatMessage
from app.services.guardrails import check_input_guardrail
from app.services.llm import (
    check_rate_limit,
    execute_and_answer,
    generate_sql,
    record_call,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Incoming NL query from the user."""
    message: str


class QueryResponse(BaseModel):
    """Returned answer, optional SQL, and tabular results."""
    answer: str
    sql: str | None = None
    results: list[dict] = []
    error: bool = False
    session_id: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
async def query_data(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    x_session_id: str = Header(default=""),
):
    """Accept a natural-language question, generate SQL, execute, and answer."""
    session_id = x_session_id or str(uuid.uuid4())

    # Layer 1: keyword guardrail
    rejection = check_input_guardrail(body.message)
    if rejection:
        return QueryResponse(answer=rejection, session_id=session_id)

    # Rate-limit check
    if not check_rate_limit(session_id):
        raise HTTPException(
            429, "Rate limit exceeded: max 10 LLM calls per minute per session."
        )

    # Load recent chat history for context
    history_rows = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
    ).scalars().all()
    chat_history = [{"role": m.role, "content": m.content} for m in reversed(history_rows)]

    # Persist user message
    db.add(ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=body.message,
    ))

    # Generate SQL from the LLM
    record_call(session_id)
    try:
        llm_result = await generate_sql(body.message, chat_history)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        await db.commit()
        return QueryResponse(answer=f"LLM error: {exc}", error=True, session_id=session_id)

    sql = llm_result.get("sql")
    explanation = llm_result.get("explanation", "")

    # Layer 2: LLM says off-topic
    if not sql:
        db.add(ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=explanation,
        ))
        await db.commit()
        return QueryResponse(answer=explanation, session_id=session_id)

    # Execute and produce grounded answer
    result = await execute_and_answer(db, body.message, sql, session_id)

    db.add(ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        sql_query=result["sql"],
    ))
    await db.commit()

    return QueryResponse(
        answer=result["answer"],
        sql=result["sql"],
        results=result["results"],
        error=result.get("error", False),
        session_id=session_id,
    )


@router.get("/chat/history")
async def get_chat_history(
    db: AsyncSession = Depends(get_db),
    x_session_id: str = Header(default=""),
):
    """Return the full chat history for a given session."""
    if not x_session_id:
        return []

    rows = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == x_session_id)
            .order_by(ChatMessage.created_at.asc())
        )
    ).scalars().all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sql_query": m.sql_query,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]
