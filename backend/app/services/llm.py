"""
OpenRouter LLM integration for the NL → SQL → Answer pipeline.

Flow:
  1. User question → LLM generates SQL (schema-injected system prompt)
  2. SQL is validated via sqlparse (SELECT-only)
  3. SQL is executed against PostgreSQL
  4. Results are fed back to the LLM for a grounded, human-readable answer
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict

import sqlparse
from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.guardrails import REJECTION_MSG

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
)

MODEL = "arcee-ai/trinity-large-preview:free"

# Rate limiter: session_id → list of UNIX timestamps
_rate_limits: dict[str, list[float]] = defaultdict(list)

# ---------------------------------------------------------------------------
# Schema description injected into every LLM system prompt
# ---------------------------------------------------------------------------
DB_SCHEMA = """\
You have access to a PostgreSQL database with the following SAP Order-to-Cash tables:

 1. business_partners (business_partner PK, customer, business_partner_name, business_partner_full_name, creation_date, business_partner_is_blocked)
 2. business_partner_addresses (business_partner FK, address_id PK, city_name, country, region, street_name, postal_code)
 3. customer_company_assignments (customer FK→business_partners.business_partner, company_code PK, reconciliation_account, payment_terms, customer_account_group)
 4. customer_sales_area_assignments (customer FK→business_partners.business_partner, sales_organization PK, distribution_channel PK, division PK, currency, customer_payment_terms, incoterms_classification)
 5. products (product PK, product_type, product_old_id, gross_weight, net_weight, weight_unit, product_group, base_unit, division)
 6. product_descriptions (product FK, language PK, product_description)
 7. plants (plant PK, plant_name, sales_organization, distribution_channel, division)
 8. product_plants (product FK, plant FK, profit_center, mrp_type, availability_check_type)
 9. product_storage_locations (product FK, plant FK, storage_location PK)
10. sales_order_headers (sales_order PK, sales_order_type, sales_organization, distribution_channel, sold_to_party FK→business_partners, total_net_amount, transaction_currency, creation_date, overall_delivery_status, requested_delivery_date, customer_payment_terms)
11. sales_order_items (sales_order FK, sales_order_item PK, material FK→products.product, requested_quantity, requested_quantity_unit, net_amount, transaction_currency, material_group, production_plant)
12. sales_order_schedule_lines (sales_order FK, sales_order_item FK, schedule_line PK, confirmed_delivery_date, confd_order_qty_by_matl_avail_check)
13. outbound_delivery_headers (delivery_document PK, creation_date, overall_goods_movement_status, overall_picking_status, shipping_point)
14. outbound_delivery_items (delivery_document FK, delivery_document_item PK, actual_delivery_quantity, plant, reference_sd_document FK→sales_order_headers.sales_order, reference_sd_document_item, storage_location)
15. billing_document_headers (billing_document PK, billing_document_type, creation_date, billing_document_date, billing_document_is_cancelled, total_net_amount, transaction_currency, company_code, fiscal_year, accounting_document, sold_to_party FK→business_partners)
16. billing_document_items (billing_document FK, billing_document_item PK, material FK→products.product, billing_quantity, net_amount, transaction_currency, reference_sd_document, reference_sd_document_item)
17. billing_document_cancellations (billing_document PK, billing_document_is_cancelled, total_net_amount, transaction_currency, sold_to_party, accounting_document)
18. journal_entry_items_accounts_receivable (company_code PK, fiscal_year PK, accounting_document PK, accounting_document_item PK, gl_account, reference_document, customer FK→business_partners, amount_in_transaction_currency, transaction_currency, posting_date, clearing_date, clearing_accounting_document)
19. payments_accounts_receivable (company_code PK, fiscal_year PK, accounting_document PK, accounting_document_item PK, customer FK→business_partners, amount_in_transaction_currency, transaction_currency, posting_date, clearing_accounting_document, invoice_reference)

Key relationships (O2C flow):
- Customer (business_partners.business_partner) → Sales Order (sold_to_party)
- Sales Order → Sales Order Items (sales_order) → Product (material)
- Sales Order → Delivery (outbound_delivery_items.reference_sd_document)
- Delivery → Billing (billing_document_items.reference_sd_document = delivery_document)
- Billing → Journal Entry (journal_entry.reference_document = billing_document)
- Journal Entry → Payment (payment.clearing_accounting_document)
"""

SYSTEM_PROMPT = (
    "You are a data analyst assistant for SAP Order-to-Cash data. "
    "You ONLY answer questions about this dataset.\n\n"
    f"{DB_SCHEMA}\n"
    "RULES:\n"
    "1. Generate ONLY SELECT queries. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, or any DDL/DML.\n"
    "2. Always use double quotes around table and column names if they contain special characters.\n"
    '3. Return your response in this exact JSON format:\n'
    '   {"sql": "SELECT ...", "explanation": "Brief explanation of what the query does"}\n'
    "4. If the question is NOT about the Order-to-Cash dataset, return:\n"
    f'   {{"sql": null, "explanation": "{REJECTION_MSG}"}}\n'
    "5. Use appropriate JOINs, aggregations, and filters based on the question.\n"
    "6. Limit results to 100 rows unless the user specifies otherwise.\n"
    "7. For amounts, always include the currency column.\n"
    "8. When querying products, JOIN with product_descriptions for readable names.\n"
)

ANSWER_PROMPT = (
    "Based on the SQL query results below, provide a clear, concise answer "
    "to the user's question.\n"
    "IMPORTANT: Your answer MUST be grounded in the actual data returned. "
    "Do NOT make up or hallucinate any information.\n"
    "If the results are empty, say so clearly.\n\n"
    "User question: {question}\n"
    "SQL query: {sql}\n"
    "Query results (first rows): {results}\n\n"
    "Provide a helpful, data-grounded answer:"
)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def check_rate_limit(session_id: str) -> bool:
    """Return ``True`` if the session is still within the per-minute rate limit."""
    now = time.time()
    timestamps = _rate_limits[session_id]
    _rate_limits[session_id] = [t for t in timestamps if now - t < 60]
    return len(_rate_limits[session_id]) < settings.llm_rate_limit


def record_call(session_id: str) -> None:
    """Record a timestamped LLM call against the given session."""
    _rate_limits[session_id].append(time.time())


# ---------------------------------------------------------------------------
# SQL validation
# ---------------------------------------------------------------------------

_DISALLOWED_SQL_KEYWORDS = frozenset([
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXEC",
])


def validate_sql(sql: str) -> bool:
    """Validate that *sql* is a pure SELECT statement with no dangerous keywords."""
    parsed = sqlparse.parse(sql)
    if not parsed:
        return False

    for statement in parsed:
        stmt_type = statement.get_type()
        if stmt_type and stmt_type.upper() != "SELECT":
            return False

    upper = sql.upper()
    for keyword in _DISALLOWED_SQL_KEYWORDS:
        if f" {keyword} " in f" {upper} ":
            return False

    return True


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> str:
    """Strip markdown code fences from an LLM response, if present."""
    if "```json" in raw:
        return raw.split("```json")[1].split("```")[0].strip()
    if "```" in raw:
        return raw.split("```")[1].split("```")[0].strip()
    return raw.strip()


async def generate_sql(
    question: str, chat_history: list[dict] | None = None
) -> dict:
    """
    Use the LLM to translate a natural-language question into SQL.

    Returns ``{"sql": str | None, "explanation": str}``.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": f"Question: {question}"})

    response = await client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.1, max_tokens=1024,
    )
    raw_text = response.choices[0].message.content.strip()

    try:
        return json.loads(_extract_json(raw_text))
    except json.JSONDecodeError:
        pass

    # Retry once with explicit formatting instruction
    logger.warning("LLM returned invalid JSON — retrying with explicit instruction.")
    messages.append({"role": "assistant", "content": raw_text})
    messages.append({
        "role": "user",
        "content": 'Please respond with valid JSON only: {"sql": "...", "explanation": "..."}',
    })

    response = await client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.0, max_tokens=1024,
    )
    return json.loads(_extract_json(response.choices[0].message.content.strip()))


def _serialise_rows(rows: list[dict], limit: int = 100) -> list[dict]:
    """Convert query result rows to JSON-safe dicts."""
    serialised: list[dict] = []
    for row in rows[:limit]:
        clean: dict = {}
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                clean[key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool, type(None))):
                clean[key] = value
            else:
                clean[key] = str(value)
        serialised.append(clean)
    return serialised


async def execute_and_answer(
    db: AsyncSession, question: str, sql: str, session_id: str,
) -> dict:
    """Execute the generated SQL and produce a grounded natural-language answer."""
    if not validate_sql(sql):
        return {
            "answer": "The generated SQL was invalid or contained disallowed operations. Please rephrase.",
            "sql": sql,
            "results": [],
            "error": True,
        }

    try:
        result = await db.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as exc:
        logger.warning("SQL execution failed: %s — asking LLM to retry.", exc)
        retry_result = await generate_sql(
            f"{question}\n\nThe previous SQL failed with: {exc}\nPlease fix the query."
        )
        if not retry_result.get("sql"):
            return {
                "answer": f"Could not generate a valid query. Error: {exc}",
                "sql": sql,
                "results": [],
                "error": True,
            }
        sql = retry_result["sql"]
        if not validate_sql(sql):
            return {
                "answer": "Retry query was also invalid.",
                "sql": sql,
                "results": [],
                "error": True,
            }
        try:
            result = await db.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as retry_exc:
            return {
                "answer": f"Query failed after retry: {retry_exc}",
                "sql": sql,
                "results": [],
                "error": True,
            }

    serialised_rows = _serialise_rows(rows)
    record_call(session_id)

    # Generate a grounded answer
    answer_input = ANSWER_PROMPT.format(
        question=question,
        sql=sql,
        results=json.dumps(serialised_rows[:20], default=str),
    )

    try:
        answer_response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": answer_input}],
            temperature=0.2,
            max_tokens=1024,
        )
        answer = answer_response.choices[0].message.content.strip()
    except Exception:
        answer = (
            f"Found {len(serialised_rows)} results. Here are the first few rows."
            if serialised_rows
            else "The query returned no results."
        )

    return {
        "answer": answer,
        "sql": sql,
        "results": serialised_rows,
        "error": False,
    }
