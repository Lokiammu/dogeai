from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class JournalEntryItemAR(Base):
    __tablename__ = "journal_entry_items_accounts_receivable"

    company_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(4), primary_key=True)
    accounting_document: Mapped[str] = mapped_column(String(20), primary_key=True)
    accounting_document_item: Mapped[str] = mapped_column(String(10), primary_key=True)
    gl_account: Mapped[str | None] = mapped_column(String(20))
    reference_document: Mapped[str | None] = mapped_column(String(20), index=True)
    cost_center: Mapped[str | None] = mapped_column(String(20))
    profit_center: Mapped[str | None] = mapped_column(String(20))
    transaction_currency: Mapped[str | None] = mapped_column(String(5))
    amount_in_transaction_currency: Mapped[float | None] = mapped_column(Numeric(15, 2))
    company_code_currency: Mapped[str | None] = mapped_column(String(5))
    amount_in_company_code_currency: Mapped[float | None] = mapped_column(Numeric(15, 2))
    posting_date: Mapped[str | None] = mapped_column(DateTime)
    document_date: Mapped[str | None] = mapped_column(DateTime)
    accounting_document_type: Mapped[str | None] = mapped_column(String(5))
    assignment_reference: Mapped[str | None] = mapped_column(String(30))
    last_change_date_time: Mapped[str | None] = mapped_column(DateTime)
    customer: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("business_partners.business_partner"), index=True
    )
    financial_account_type: Mapped[str | None] = mapped_column(String(5))
    clearing_date: Mapped[str | None] = mapped_column(DateTime)
    clearing_accounting_document: Mapped[str | None] = mapped_column(String(20))
    clearing_doc_fiscal_year: Mapped[str | None] = mapped_column(String(4))


class PaymentAR(Base):
    __tablename__ = "payments_accounts_receivable"

    company_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(4), primary_key=True)
    accounting_document: Mapped[str] = mapped_column(String(20), primary_key=True)
    accounting_document_item: Mapped[str] = mapped_column(String(10), primary_key=True)
    clearing_date: Mapped[str | None] = mapped_column(DateTime)
    clearing_accounting_document: Mapped[str | None] = mapped_column(String(20))
    clearing_doc_fiscal_year: Mapped[str | None] = mapped_column(String(4))
    amount_in_transaction_currency: Mapped[float | None] = mapped_column(Numeric(15, 2))
    transaction_currency: Mapped[str | None] = mapped_column(String(5))
    amount_in_company_code_currency: Mapped[float | None] = mapped_column(Numeric(15, 2))
    company_code_currency: Mapped[str | None] = mapped_column(String(5))
    customer: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("business_partners.business_partner"), index=True
    )
    invoice_reference: Mapped[str | None] = mapped_column(String(20))
    invoice_reference_fiscal_year: Mapped[str | None] = mapped_column(String(4))
    sales_document: Mapped[str | None] = mapped_column(String(20))
    sales_document_item: Mapped[str | None] = mapped_column(String(10))
    posting_date: Mapped[str | None] = mapped_column(DateTime)
    document_date: Mapped[str | None] = mapped_column(DateTime)
    assignment_reference: Mapped[str | None] = mapped_column(String(30))
    gl_account: Mapped[str | None] = mapped_column(String(20))
    financial_account_type: Mapped[str | None] = mapped_column(String(5))
    profit_center: Mapped[str | None] = mapped_column(String(20))
    cost_center: Mapped[str | None] = mapped_column(String(20))
