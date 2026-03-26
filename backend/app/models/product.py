from sqlalchemy import String, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    product: Mapped[str] = mapped_column(String(40), primary_key=True)
    product_type: Mapped[str | None] = mapped_column(String(10))
    cross_plant_status: Mapped[str | None] = mapped_column(String(5))
    cross_plant_status_validity_date: Mapped[str | None] = mapped_column(DateTime)
    creation_date: Mapped[str | None] = mapped_column(DateTime)
    created_by_user: Mapped[str | None] = mapped_column(String(20))
    last_change_date: Mapped[str | None] = mapped_column(DateTime)
    last_change_date_time: Mapped[str | None] = mapped_column(DateTime)
    is_marked_for_deletion: Mapped[bool | None] = mapped_column(Boolean, default=False)
    product_old_id: Mapped[str | None] = mapped_column(String(40))
    gross_weight: Mapped[float | None] = mapped_column(Numeric(15, 3))
    weight_unit: Mapped[str | None] = mapped_column(String(5))
    net_weight: Mapped[float | None] = mapped_column(Numeric(15, 3))
    product_group: Mapped[str | None] = mapped_column(String(20))
    base_unit: Mapped[str | None] = mapped_column(String(5))
    division: Mapped[str | None] = mapped_column(String(10))
    industry_sector: Mapped[str | None] = mapped_column(String(5))

    descriptions: Mapped[list["ProductDescription"]] = relationship(back_populates="product_ref")


class ProductDescription(Base):
    __tablename__ = "product_descriptions"

    product: Mapped[str] = mapped_column(
        String(40), ForeignKey("products.product"), primary_key=True
    )
    language: Mapped[str] = mapped_column(String(5), primary_key=True)
    product_description: Mapped[str | None] = mapped_column(String(200))

    product_ref: Mapped["Product"] = relationship(back_populates="descriptions")


class Plant(Base):
    __tablename__ = "plants"

    plant: Mapped[str] = mapped_column(String(10), primary_key=True)
    plant_name: Mapped[str | None] = mapped_column(String(100))
    valuation_area: Mapped[str | None] = mapped_column(String(10))
    plant_customer: Mapped[str | None] = mapped_column(String(20))
    plant_supplier: Mapped[str | None] = mapped_column(String(20))
    factory_calendar: Mapped[str | None] = mapped_column(String(10))
    default_purchasing_organization: Mapped[str | None] = mapped_column(String(10))
    sales_organization: Mapped[str | None] = mapped_column(String(10))
    address_id: Mapped[str | None] = mapped_column(String(20))
    plant_category: Mapped[str | None] = mapped_column(String(5))
    distribution_channel: Mapped[str | None] = mapped_column(String(10))
    division: Mapped[str | None] = mapped_column(String(10))
    language: Mapped[str | None] = mapped_column(String(5))
    is_marked_for_archiving: Mapped[bool | None] = mapped_column(Boolean, default=False)


class ProductPlant(Base):
    __tablename__ = "product_plants"

    product: Mapped[str] = mapped_column(
        String(40), ForeignKey("products.product"), primary_key=True
    )
    plant: Mapped[str] = mapped_column(
        String(10), ForeignKey("plants.plant"), primary_key=True
    )
    country_of_origin: Mapped[str | None] = mapped_column(String(5))
    region_of_origin: Mapped[str | None] = mapped_column(String(10))
    production_invtry_managed_loc: Mapped[str | None] = mapped_column(String(10))
    availability_check_type: Mapped[str | None] = mapped_column(String(5))
    fiscal_year_variant: Mapped[str | None] = mapped_column(String(5))
    profit_center: Mapped[str | None] = mapped_column(String(20))
    mrp_type: Mapped[str | None] = mapped_column(String(5))


class ProductStorageLocation(Base):
    __tablename__ = "product_storage_locations"

    product: Mapped[str] = mapped_column(
        String(40), ForeignKey("products.product"), primary_key=True
    )
    plant: Mapped[str] = mapped_column(
        String(10), ForeignKey("plants.plant"), primary_key=True
    )
    storage_location: Mapped[str] = mapped_column(String(10), primary_key=True)
    physical_inventory_block_ind: Mapped[str | None] = mapped_column(String(5))
    date_of_last_posted_cnt_un_rstrcd_stk: Mapped[str | None] = mapped_column(DateTime)
