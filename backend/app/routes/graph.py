"""Graph endpoints — full O2C graph and node expansion."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.graph_builder import build_full_graph, expand_node

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def get_graph(db: AsyncSession = Depends(get_db)):
    """Return the full O2C graph as ``{nodes, edges}``."""
    return await build_full_graph(db)


@router.get("/node/{node_id}/expand")
async def get_node_expansion(node_id: str, db: AsyncSession = Depends(get_db)):
    """Return the 1-hop neighbourhood subgraph around *node_id*."""
    return await expand_node(db, node_id)
