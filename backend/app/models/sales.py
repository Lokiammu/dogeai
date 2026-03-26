from sqlalchemy import String, Numeric, DateTime, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SalesOrderHeader(Base):
    __tablename__ = "sales_order_headers"

    sales_order: Mapped[str] = mapped_column(String(20), primary_key=True)
    sales_order_type: Mapped[str | None] = mapped_column(String(10))
    sales_organization: Mapped[str | None] = mapped_column(String(10))
    distribution_channel: Mapped[str | None] = mapped_column(String(10))
    organization_division: Mapped[str | None] = mapped_column(String(10))
    sales_group: Mapped[str | None] = mapped_column(String(10))
    sales_office: Mapped[str | None] = mapped_column(String(10))
    sold_to_party: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("business_partners.business_partner"), index=True
    )
    creation_date: Mapped[str | None] = mapped_column(DateTime)
    created_by_user: Mapped[str | None] = mapped_column(String(20))
    last_change_date_time: Mapped[str | None] = mapped_column(DateTime)
    total_net_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    overall_delivery_status: Mapped[str | None] = mapped_column(String(5))
    overall_ord_reltd_billg_status: Mapped[str | None] = mapped_column(String(5))
    overall_sd_doc_reference_status: Mapped[str | None] = mapped_column(String(5))
    transaction_currency: Mapped[str | None] = mapped_column(String(5))
    pricing_date: Mapped[str | None] = mapped_column(DateTime)
    requested_delivery_date: Mapped[str | None] = mapped_column(DateTime)
    header_billing_block_reason: Mapped[str | None] = mapped_column(String(10))
    delivery_block_reason: Mapped[str | None] = mapped_column(String(10))
    incoterms_classification: Mapped[str | None] = mapped_column(String(10))
    incoterms_location1: Mapped[str | None] = mapped_column(String(100))
    customer_payment_terms: Mapped[str | None] = mapped_column(String(10))
    total_credit_check_status: Mapped[str | None] = mapped_column(String(5))

    items: Mapped[list["SalesOrderItem"]] = relationship(back_populates="header")
    partner: Mapped["BusinessPartner | None"] = relationship()


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    sales_order: Mapped[str] = mapped_column(
        String(20), ForeignKey("sales_order_headers.sales_order"), primary_key=True
    )
    sales_order_item: Mapped[str] = mapped_column(String(10), primary_key=True)
    sales_order_item_category: Mapped[str | None] = mapped_column(String(10))
    material: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("products.product"), index=True
    )
    requested_quantity: Mapped[float | None] = mapped_column(Numeric(15, 3))
    requested_quantity_unit: Mapped[str | None] = mapped_column(String(5))
    transaction_currency: Mapped[str | None] = mapped_column(String(5))
    net_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    material_group: Mapped[str | None] = mapped_column(String(20))
    production_plant: Mapped[str | None] = mapped_column(String(10))
    storage_location: Mapped[str | None] = mapped_column(String(10))
    sales_document_rjcn_reason: Mapped[str | None] = mapped_column(String(10))
    item_billing_block_reason: Mapped[str | None] = mapped_column(String(10))

    header: Mapped["SalesOrderHeader"] = relationship(back_populates="items")
    schedule_lines: Mapped[list["SalesOrderScheduleLine"]] = relationship(back_populates="item")
    product: Mapped["Product | None"] = relationship()


class SalesOrderScheduleLine(Base):
    __tablename__ = "sales_order_schedule_lines"

    sales_order: Mapped[str] = mapped_column(String(20), primary_key=True)
    sales_order_item: Mapped[str] = mapped_column(String(10), primary_key=True)
    schedule_line: Mapped[str] = mapped_column(String(10), primary_key=True)
    confirmed_delivery_date: Mapped[str | None] = mapped_column(DateTime)
    order_quantity_unit: Mapped[str | None] = mapped_column(String(5))
    confd_order_qty_by_matl_avail_check: Mapped[float | None] = mapped_column(Numeric(15, 3))

    item: Mapped["SalesOrderItem"] = relationship(back_populates="schedule_lines")

    __table_args__ = (
        ForeignKeyConstraint(
            ["sales_order", "sales_order_item"],
            ["sales_order_items.sales_order", "sales_order_items.sales_order_item"],
        ),
    )


# Avoid circular import at module level
from app.models.partner import BusinessPartner  # noqa: E402
from app.models.product import Product  # noqa: E402
