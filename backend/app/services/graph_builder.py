"""
Build a NetworkX directed graph representing the SAP Order-to-Cash flow.

Node types : Customer, SalesOrder, Delivery, BillingDoc, JournalEntry, Payment, Product
Edge flow  : Customer → SalesOrder → Delivery → BillingDoc → JournalEntry → Payment
             SalesOrder → Product
"""
from __future__ import annotations

import logging

import networkx as nx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def build_full_graph(db: AsyncSession) -> dict:
    """Build the complete O2C graph and return a JSON-serialisable dict."""
    G = nx.DiGraph()

    await _add_customers(G, db)
    await _add_products(G, db)
    await _add_sales_orders(G, db)
    await _add_deliveries(G, db)
    await _add_billing_documents(G, db)
    await _add_journal_entries(G, db)
    await _add_payments(G, db)

    logger.info("Graph built: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    return _serialise_graph(G)


async def expand_node(db: AsyncSession, node_id: str) -> dict:
    """Return the 1-hop neighbourhood subgraph around *node_id*."""
    full = await build_full_graph(db)

    G = nx.DiGraph()
    for n in full["nodes"]:
        G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
    for e in full["edges"]:
        G.add_edge(
            e["source"], e["target"],
            **{k: v for k, v in e.items() if k not in ("source", "target")},
        )

    if node_id not in G:
        return {"nodes": [], "edges": []}

    neighbours = set(G.predecessors(node_id)) | set(G.successors(node_id))
    neighbours.add(node_id)
    return _serialise_graph(G.subgraph(neighbours))


# ---------------------------------------------------------------------------
# Private graph-population helpers
# ---------------------------------------------------------------------------

async def _add_customers(G: nx.DiGraph, db: AsyncSession) -> None:
    rows = (await db.execute(text(
        "SELECT bp.business_partner, bp.business_partner_name, "
        "bpa.city_name, bpa.country "
        "FROM business_partners bp "
        "LEFT JOIN business_partner_addresses bpa "
        "ON bp.business_partner = bpa.business_partner"
    ))).fetchall()
    for r in rows:
        G.add_node(
            f"Customer:{r[0]}", type="Customer", id=r[0],
            label=r[1] or r[0], city=r[2], country=r[3],
        )


async def _add_products(G: nx.DiGraph, db: AsyncSession) -> None:
    rows = (await db.execute(text(
        "SELECT p.product, pd.product_description, p.product_type "
        "FROM products p "
        "LEFT JOIN product_descriptions pd "
        "ON p.product = pd.product AND pd.language = 'EN'"
    ))).fetchall()
    for r in rows:
        G.add_node(
            f"Product:{r[0]}", type="Product", id=r[0],
            label=r[1] or r[0], product_type=r[2],
        )


async def _add_sales_orders(G: nx.DiGraph, db: AsyncSession) -> None:
    # Headers
    rows = (await db.execute(text(
        "SELECT sales_order, sold_to_party, total_net_amount, "
        "transaction_currency, creation_date, overall_delivery_status "
        "FROM sales_order_headers"
    ))).fetchall()
    for r in rows:
        G.add_node(
            f"SalesOrder:{r[0]}", type="SalesOrder", id=r[0],
            label=f"SO {r[0]}",
            amount=float(r[2]) if r[2] else None,
            currency=r[3], status=r[5],
            date=r[4].isoformat() if r[4] else None,
        )
        if r[1]:
            G.add_edge(f"Customer:{r[1]}", f"SalesOrder:{r[0]}", relation="PLACED_ORDER")

    # Items → Product links
    rows = (await db.execute(text(
        "SELECT sales_order, material, net_amount FROM sales_order_items"
    ))).fetchall()
    for r in rows:
        if r[1] and G.has_node(f"Product:{r[1]}"):
            G.add_edge(
                f"SalesOrder:{r[0]}", f"Product:{r[1]}",
                relation="CONTAINS_PRODUCT",
                amount=float(r[2]) if r[2] else None,
            )


async def _add_deliveries(G: nx.DiGraph, db: AsyncSession) -> None:
    rows = (await db.execute(text(
        "SELECT delivery_document, creation_date, "
        "overall_goods_movement_status, shipping_point "
        "FROM outbound_delivery_headers"
    ))).fetchall()
    for r in rows:
        G.add_node(
            f"Delivery:{r[0]}", type="Delivery", id=r[0],
            label=f"DL {r[0]}", status=r[2], shipping_point=r[3],
            date=r[1].isoformat() if r[1] else None,
        )

    # Delivery → Sales Order links
    rows = (await db.execute(text(
        "SELECT DISTINCT delivery_document, reference_sd_document "
        "FROM outbound_delivery_items "
        "WHERE reference_sd_document IS NOT NULL"
    ))).fetchall()
    for r in rows:
        if G.has_node(f"SalesOrder:{r[1]}"):
            G.add_edge(f"SalesOrder:{r[1]}", f"Delivery:{r[0]}", relation="DELIVERED_VIA")


async def _add_billing_documents(G: nx.DiGraph, db: AsyncSession) -> None:
    rows = (await db.execute(text(
        "SELECT billing_document, sold_to_party, total_net_amount, "
        "transaction_currency, creation_date, billing_document_is_cancelled "
        "FROM billing_document_headers"
    ))).fetchall()
    for r in rows:
        G.add_node(
            f"BillingDoc:{r[0]}", type="BillingDoc", id=r[0],
            label=f"INV {r[0]}",
            amount=float(r[2]) if r[2] else None,
            currency=r[3], cancelled=r[5],
            date=r[4].isoformat() if r[4] else None,
        )
        if r[1]:
            G.add_edge(f"Customer:{r[1]}", f"BillingDoc:{r[0]}", relation="BILLED_TO")

    # Billing → Delivery links
    rows = (await db.execute(text(
        "SELECT DISTINCT billing_document, reference_sd_document "
        "FROM billing_document_items "
        "WHERE reference_sd_document IS NOT NULL"
    ))).fetchall()
    for r in rows:
        if G.has_node(f"Delivery:{r[1]}"):
            G.add_edge(f"Delivery:{r[1]}", f"BillingDoc:{r[0]}", relation="INVOICED_FROM")


async def _add_journal_entries(G: nx.DiGraph, db: AsyncSession) -> None:
    rows = (await db.execute(text(
        "SELECT company_code, fiscal_year, accounting_document, customer, "
        "reference_document, amount_in_transaction_currency, "
        "transaction_currency, posting_date "
        "FROM journal_entry_items_accounts_receivable "
        "WHERE accounting_document_item = '1'"
    ))).fetchall()
    for r in rows:
        je_id = f"{r[0]}-{r[1]}-{r[2]}"
        G.add_node(
            f"JournalEntry:{je_id}", type="JournalEntry", id=je_id,
            label=f"JE {r[2]}",
            amount=float(r[5]) if r[5] else None,
            currency=r[6],
            date=r[7].isoformat() if r[7] else None,
        )
        if r[4] and G.has_node(f"BillingDoc:{r[4]}"):
            G.add_edge(f"BillingDoc:{r[4]}", f"JournalEntry:{je_id}", relation="POSTED_AS")
        if r[3]:
            G.add_edge(f"JournalEntry:{je_id}", f"Customer:{r[3]}", relation="RECEIVABLE_FROM")


async def _add_payments(G: nx.DiGraph, db: AsyncSession) -> None:
    rows = (await db.execute(text(
        "SELECT company_code, fiscal_year, accounting_document, customer, "
        "amount_in_transaction_currency, transaction_currency, posting_date, "
        "clearing_accounting_document, clearing_doc_fiscal_year "
        "FROM payments_accounts_receivable "
        "WHERE accounting_document_item = '1'"
    ))).fetchall()
    for r in rows:
        pay_id = f"{r[0]}-{r[1]}-{r[2]}"
        G.add_node(
            f"Payment:{pay_id}", type="Payment", id=pay_id,
            label=f"PAY {r[2]}",
            amount=float(r[4]) if r[4] else None,
            currency=r[5],
            date=r[6].isoformat() if r[6] else None,
        )
        if r[7]:
            clearing_id = f"{r[0]}-{r[8]}-{r[7]}"
            if G.has_node(f"JournalEntry:{clearing_id}"):
                G.add_edge(
                    f"JournalEntry:{clearing_id}", f"Payment:{pay_id}",
                    relation="CLEARED_BY",
                )
        if r[3]:
            G.add_edge(f"Payment:{pay_id}", f"Customer:{r[3]}", relation="PAID_BY")


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _serialise_graph(G: nx.DiGraph) -> dict:
    """Convert a NetworkX graph to a JSON-serialisable ``{nodes, edges}`` dict."""
    nodes = [{**data, "id": nid} for nid, data in G.nodes(data=True)]
    edges = [{**data, "source": src, "target": tgt} for src, tgt, data in G.edges(data=True)]
    return {"nodes": nodes, "edges": edges}
