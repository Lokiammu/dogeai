"""
Ingest all JSONL files from sap-o2c-data/ into PostgreSQL.

Usage:
    python -m app.ingest
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Integer, Numeric, text

from app.config import get_settings
from app.database import engine
from app.models.base import Base

import app.models  # noqa: F401 — register all models with Base.metadata

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------

_CAMEL_RE_1 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_RE_2 = re.compile(r"([a-z0-9])([A-Z])")


def _to_snake(name: str) -> str:
    """Convert a camelCase name to snake_case."""
    s1 = _CAMEL_RE_1.sub(r"\1_\2", name)
    return _CAMEL_RE_2.sub(r"\1_\2", s1).lower()


# ---------------------------------------------------------------------------
# Entity → table mapping (directory name → table name)
# ---------------------------------------------------------------------------

ENTITY_TABLE_MAP: dict[str, str] = {
    "business_partners":                       "business_partners",
    "business_partner_addresses":              "business_partner_addresses",
    "customer_company_assignments":            "customer_company_assignments",
    "customer_sales_area_assignments":         "customer_sales_area_assignments",
    "products":                                "products",
    "product_descriptions":                    "product_descriptions",
    "plants":                                  "plants",
    "product_plants":                          "product_plants",
    "product_storage_locations":               "product_storage_locations",
    "sales_order_headers":                     "sales_order_headers",
    "sales_order_items":                       "sales_order_items",
    "sales_order_schedule_lines":              "sales_order_schedule_lines",
    "outbound_delivery_headers":               "outbound_delivery_headers",
    "outbound_delivery_items":                 "outbound_delivery_items",
    "billing_document_headers":                "billing_document_headers",
    "billing_document_items":                  "billing_document_items",
    "billing_document_cancellations":          "billing_document_cancellations",
    "journal_entry_items_accounts_receivable": "journal_entry_items_accounts_receivable",
    "payments_accounts_receivable":            "payments_accounts_receivable",
}

# Ingestion order respects FK dependencies (parents first).
INGEST_ORDER: list[str] = list(ENTITY_TABLE_MAP.keys())

# Fields containing nested time objects: field_name → flattened columns
TIME_FIELDS: dict[str, tuple[str, str, str]] = {
    "creationTime": (
        "creation_time_hours", "creation_time_minutes", "creation_time_seconds",
    ),
    "actualGoodsMovementTime": (
        "actual_goods_movement_time_hours",
        "actual_goods_movement_time_minutes",
        "actual_goods_movement_time_seconds",
    ),
}


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------

def _parse_datetime(value: object) -> datetime | None:
    """Parse an ISO datetime string to a timezone-naive ``datetime``."""
    if value is None or isinstance(value, datetime):
        return value  # type: ignore[return-value]
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _coerce_value(value: object, column) -> object:
    """Coerce a JSON value to the expected SQLAlchemy column type."""
    if value is None or value == "":
        return None

    col_type = type(column.type)

    if col_type is DateTime:
        return _parse_datetime(value)
    if col_type is Numeric:
        try:
            return float(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None
    if col_type is Boolean:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    if col_type is Integer:
        try:
            return int(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None

    return value


def _transform_row(row: dict, table_name: str) -> dict:
    """Transform a raw JSONL row to match the database schema."""
    table = Base.metadata.tables.get(table_name)
    if table is None:
        raise ValueError(f"Unknown table: {table_name}")

    col_map = {c.name: c for c in table.columns}
    valid_columns = set(col_map.keys())
    result: dict = {}

    for key, value in row.items():
        # Flatten nested time objects
        if key in TIME_FIELDS and isinstance(value, dict):
            h_col, m_col, s_col = TIME_FIELDS[key]
            if h_col in valid_columns:
                result[h_col] = value.get("hours")
            if m_col in valid_columns:
                result[m_col] = value.get("minutes")
            if s_col in valid_columns:
                result[s_col] = value.get("seconds")
            continue

        snake_key = _to_snake(key)
        if snake_key in valid_columns:
            result[snake_key] = _coerce_value(value, col_map[snake_key])

    return result


# ---------------------------------------------------------------------------
# Ingestion pipeline
# ---------------------------------------------------------------------------

BATCH_SIZE = 500


async def _ingest_entity(entity_dir: str, table_name: str) -> None:
    """Load all JSONL files for one entity into the database."""
    data_path = Path(settings.data_dir) / entity_dir
    if not data_path.exists():
        logger.warning("SKIP %s — directory not found", entity_dir)
        return

    rows: list[dict] = []
    for jsonl_file in sorted(data_path.glob("*.jsonl")):
        with open(jsonl_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(_transform_row(json.loads(line), table_name))

    if not rows:
        logger.info("SKIP %s — no rows found", entity_dir)
        return

    table = Base.metadata.tables[table_name]
    async with engine.begin() as conn:
        await conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
        for i in range(0, len(rows), BATCH_SIZE):
            await conn.execute(table.insert(), rows[i : i + BATCH_SIZE])

    logger.info("OK   %s — %d rows ingested", entity_dir, len(rows))


async def main() -> None:
    """Create tables and ingest all SAP O2C entity data."""
    logger.info("Creating tables …")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created.\n")

    logger.info("Ingesting data …")
    for entity_dir in INGEST_ORDER:
        await _ingest_entity(entity_dir, ENTITY_TABLE_MAP[entity_dir])

    logger.info("\nIngestion complete!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
