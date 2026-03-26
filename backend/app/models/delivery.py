from sqlalchemy import String, Numeric, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class OutboundDeliveryHeader(Base):
    __tablename__ = "outbound_delivery_headers"

    delivery_document: Mapped[str] = mapped_column(String(20), primary_key=True)
    actual_goods_movement_date: Mapped[str | None] = mapped_column(DateTime)
    actual_goods_movement_time_hours: Mapped[int | None] = mapped_column(Integer)
    actual_goods_movement_time_minutes: Mapped[int | None] = mapped_column(Integer)
    actual_goods_movement_time_seconds: Mapped[int | None] = mapped_column(Integer)
    creation_date: Mapped[str | None] = mapped_column(DateTime)
    creation_time_hours: Mapped[int | None] = mapped_column(Integer)
    creation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    creation_time_seconds: Mapped[int | None] = mapped_column(Integer)
    delivery_block_reason: Mapped[str | None] = mapped_column(String(10))
    hdr_general_incompletion_status: Mapped[str | None] = mapped_column(String(5))
    header_billing_block_reason: Mapped[str | None] = mapped_column(String(10))
    last_change_date: Mapped[str | None] = mapped_column(DateTime)
    overall_goods_movement_status: Mapped[str | None] = mapped_column(String(5))
    overall_picking_status: Mapped[str | None] = mapped_column(String(5))
    overall_proof_of_delivery_status: Mapped[str | None] = mapped_column(String(5))
    shipping_point: Mapped[str | None] = mapped_column(String(10))

    items: Mapped[list["OutboundDeliveryItem"]] = relationship(back_populates="header")


class OutboundDeliveryItem(Base):
    __tablename__ = "outbound_delivery_items"

    delivery_document: Mapped[str] = mapped_column(
        String(20), ForeignKey("outbound_delivery_headers.delivery_document"), primary_key=True
    )
    delivery_document_item: Mapped[str] = mapped_column(String(10), primary_key=True)
    actual_delivery_quantity: Mapped[float | None] = mapped_column(Numeric(15, 3))
    batch: Mapped[str | None] = mapped_column(String(20))
    delivery_quantity_unit: Mapped[str | None] = mapped_column(String(5))
    item_billing_block_reason: Mapped[str | None] = mapped_column(String(10))
    last_change_date: Mapped[str | None] = mapped_column(DateTime)
    plant: Mapped[str | None] = mapped_column(String(10))
    reference_sd_document: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("sales_order_headers.sales_order"), index=True
    )
    reference_sd_document_item: Mapped[str | None] = mapped_column(String(10))
    storage_location: Mapped[str | None] = mapped_column(String(10))

    header: Mapped["OutboundDeliveryHeader"] = relationship(back_populates="items")
    sales_order: Mapped["SalesOrderHeader | None"] = relationship()


from app.models.sales import SalesOrderHeader  # noqa: E402
