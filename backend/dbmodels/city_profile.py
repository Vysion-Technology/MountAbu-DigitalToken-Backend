from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from backend.database import Base


class CityProfile(Base):
    __tablename__ = "city_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Basic city profile fields (kept optional so partial updates are supported)
    area_sq_km: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    no_of_wards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ward_boundaries: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    population_estimate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rental_properties_of_corporation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    number_of_slums: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    solid_waste_per_day: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    street_light_poles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    employees_in_board: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # No. of Households
    households_residential: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    households_shops_offices: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    households_open_plots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Birth/Death
    birth_registration_per_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    birth_certificate_per_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Audit
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship (optional, useful for joins)
    created_by = relationship("User")
