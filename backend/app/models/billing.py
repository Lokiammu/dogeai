from sqlalchemy import String, Numeric, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class BillingDocumentHeader(Base):
    __tablename__ = "billing_document_headers"

    billing_document: Mapped[str] = mapped_column(String(20), primary_key=True)
    billing_document_type: Mapped[str | None] = mapped_column(String(10))
    creation_date: Mapped[str | None] = mapped_column(DateTime)
    creation_time_hours: Mapped[int | None] = mapped_column(Integer)
    creation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    creation_time_seconds: Mapped[int | None] = mapped_column(Integer)
    last_change_date_time: Mapped[str | None] = mapped_column(DateTime)
    billing_document_date: Mapped[str | None] = mapped_column(DateTime)
    billing_document_is_cancelled: Mapped[bool | None] = mapped_column(Boolean, default=False)
    cancelled_billing_document: Mapped[str | None] = mapped_column(String(20))
    total_net_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    transaction_currency: Mapped[str | None] = mapped_column(String(5))
    company_code: Mapped[str | None] = mapped_column(String(10))
    fiscal_year: Mapped[str | None] = mapped_column(String(4))
    accounting_document: Mapped[str | None] = mapped_column(String(20))
    sold_to_party: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("business_partners.business_partner"), index=True
    )

    items: Mapped[list["BillingDocumentItem"]] = relationship(back_populates="header")
    partner: Mapped["BusinessPartner | None"] = relationship()


class BillingDocumentItem(Base):
    __tablename__ = "billing_document_items"

    billing_document: Mapped[str] = mapped_column(
        String(20), ForeignKey("billing_document_headers.billing_document"), primary_key=True
    )
    billing_document_item: Mapped[str] = mapped_column(String(10), primary_key=True)
    material: Mapped[str | None] = mapped_column(String(40), ForeignKey("products.product"))
    billing_quantity: Mapped[float | None] = mapped_column(Numeric(15, 3))
    billing_quantity_unit: Mapped[str | None] = mapped_column(String(5))
    net_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    transaction_currency: Mapped[str | None] = mapped_column(String(5))
    reference_sd_document: Mapped[str | None] = mapped_column(String(20), index=True)
    reference_sd_document_item: Mapped[str | None] = mapped_column(String(10))

    header: Mapped["BillingDocumentHeader"] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()


class BillingDocumentCancellation(Base):
    __tablename__ = "billing_document_cancellations"

    billing_document: Mapped[str] = mapped_column(String(20), primary_key=True)
    billing_document_type: Mapped[str | None] = mapped_column(String(10))
    creation_date: Mapped[str | None] = mapped_column(DateTime)
    creation_time_hours: Mapped[int | None] = mapped_column(Integer)
    creation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    creation_time_seconds: Mapped[int | None] = mapped_column(Integer)
    last_change_date_time: Mapped[str | None] = mapped_column(DateTime)
    billing_document_date: Mapped[str | None] = mapped_column(DateTime)
    billing_document_is_cancelled: Mapped[bool | None] = mapped_column(Boolean, default=True)
    cancelled_billing_document: Mapped[str | None] = mapped_column(String(20))
    total_net_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    transaction_currency: Mapped[str | None] = mapped_column(String(5))
    company_code: Mapped[str | None] = mapped_column(String(10))
    fiscal_year: Mapped[str | None] = mapped_column(String(4))
    accounting_document: Mapped[str | None] = mapped_column(String(20))
    sold_to_party: Mapped[str | None] = mapped_column(String(20), index=True)


from app.models.partner import BusinessPartner  # noqa: E402
from app.models.product import Product  # noqa: E402
