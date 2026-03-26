from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class BusinessPartner(Base):
    __tablename__ = "business_partners"

    business_partner: Mapped[str] = mapped_column(String(20), primary_key=True)
    customer: Mapped[str | None] = mapped_column(String(20), index=True)
    business_partner_category: Mapped[str | None] = mapped_column(String(5))
    business_partner_full_name: Mapped[str | None] = mapped_column(String(200))
    business_partner_grouping: Mapped[str | None] = mapped_column(String(10))
    business_partner_name: Mapped[str | None] = mapped_column(String(200))
    correspondence_language: Mapped[str | None] = mapped_column(String(5))
    created_by_user: Mapped[str | None] = mapped_column(String(20))
    creation_date: Mapped[str | None] = mapped_column(DateTime)
    creation_time_hours: Mapped[int | None] = mapped_column(Integer)
    creation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    creation_time_seconds: Mapped[int | None] = mapped_column(Integer)
    first_name: Mapped[str | None] = mapped_column(String(100))
    form_of_address: Mapped[str | None] = mapped_column(String(10))
    industry: Mapped[str | None] = mapped_column(String(20))
    last_change_date: Mapped[str | None] = mapped_column(DateTime)
    last_name: Mapped[str | None] = mapped_column(String(100))
    organization_bp_name1: Mapped[str | None] = mapped_column(String(200))
    organization_bp_name2: Mapped[str | None] = mapped_column(String(200))
    business_partner_is_blocked: Mapped[bool | None] = mapped_column(Boolean, default=False)
    is_marked_for_archiving: Mapped[bool | None] = mapped_column(Boolean, default=False)

    addresses: Mapped[list["BusinessPartnerAddress"]] = relationship(back_populates="partner")


class BusinessPartnerAddress(Base):
    __tablename__ = "business_partner_addresses"

    business_partner: Mapped[str] = mapped_column(
        String(20), ForeignKey("business_partners.business_partner"), primary_key=True
    )
    address_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    validity_start_date: Mapped[str | None] = mapped_column(DateTime)
    validity_end_date: Mapped[str | None] = mapped_column(DateTime)
    address_uuid: Mapped[str | None] = mapped_column(String(50))
    address_time_zone: Mapped[str | None] = mapped_column(String(20))
    city_name: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(5))
    po_box: Mapped[str | None] = mapped_column(String(20))
    po_box_deviating_city_name: Mapped[str | None] = mapped_column(String(100))
    po_box_deviating_country: Mapped[str | None] = mapped_column(String(5))
    po_box_deviating_region: Mapped[str | None] = mapped_column(String(10))
    po_box_is_without_number: Mapped[bool | None] = mapped_column(Boolean, default=False)
    po_box_lobby_name: Mapped[str | None] = mapped_column(String(100))
    po_box_postal_code: Mapped[str | None] = mapped_column(String(20))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    region: Mapped[str | None] = mapped_column(String(10))
    street_name: Mapped[str | None] = mapped_column(String(200))
    tax_jurisdiction: Mapped[str | None] = mapped_column(String(20))
    transport_zone: Mapped[str | None] = mapped_column(String(20))

    partner: Mapped["BusinessPartner"] = relationship(back_populates="addresses")


class CustomerCompanyAssignment(Base):
    __tablename__ = "customer_company_assignments"

    customer: Mapped[str] = mapped_column(
        String(20), ForeignKey("business_partners.business_partner"), primary_key=True
    )
    company_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    accounting_clerk: Mapped[str | None] = mapped_column(String(10))
    accounting_clerk_fax_number: Mapped[str | None] = mapped_column(String(50))
    accounting_clerk_internet_address: Mapped[str | None] = mapped_column(String(200))
    accounting_clerk_phone_number: Mapped[str | None] = mapped_column(String(50))
    alternative_payer_account: Mapped[str | None] = mapped_column(String(20))
    payment_blocking_reason: Mapped[str | None] = mapped_column(String(10))
    payment_methods_list: Mapped[str | None] = mapped_column(String(20))
    payment_terms: Mapped[str | None] = mapped_column(String(10))
    reconciliation_account: Mapped[str | None] = mapped_column(String(20))
    deletion_indicator: Mapped[bool | None] = mapped_column(Boolean, default=False)
    customer_account_group: Mapped[str | None] = mapped_column(String(10))


class CustomerSalesAreaAssignment(Base):
    __tablename__ = "customer_sales_area_assignments"

    customer: Mapped[str] = mapped_column(
        String(20), ForeignKey("business_partners.business_partner"), primary_key=True
    )
    sales_organization: Mapped[str] = mapped_column(String(10), primary_key=True)
    distribution_channel: Mapped[str] = mapped_column(String(10), primary_key=True)
    division: Mapped[str] = mapped_column(String(10), primary_key=True)
    billing_is_blocked_for_customer: Mapped[str | None] = mapped_column(String(5))
    complete_delivery_is_defined: Mapped[bool | None] = mapped_column(Boolean, default=False)
    credit_control_area: Mapped[str | None] = mapped_column(String(10))
    currency: Mapped[str | None] = mapped_column(String(5))
    customer_payment_terms: Mapped[str | None] = mapped_column(String(10))
    delivery_priority: Mapped[str | None] = mapped_column(String(5))
    incoterms_classification: Mapped[str | None] = mapped_column(String(10))
    incoterms_location1: Mapped[str | None] = mapped_column(String(100))
    sales_group: Mapped[str | None] = mapped_column(String(10))
    sales_office: Mapped[str | None] = mapped_column(String(10))
    shipping_condition: Mapped[str | None] = mapped_column(String(10))
    sls_unlmtd_ovrdeliv_is_allwd: Mapped[bool | None] = mapped_column(Boolean, default=False)
    supplying_plant: Mapped[str | None] = mapped_column(String(10))
    sales_district: Mapped[str | None] = mapped_column(String(10))
    exchange_rate_type: Mapped[str | None] = mapped_column(String(10))
