from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CityProfileResponse(BaseModel):
    id: int

    area_sq_km: Optional[str] = None
    no_of_wards: Optional[int] = None
    ward_boundaries: Optional[str] = None
    population_estimate: Optional[int] = None
    rental_properties_of_corporation: Optional[int] = None
    number_of_slums: Optional[int] = None
    solid_waste_per_day: Optional[str] = None
    street_light_poles: Optional[int] = None
    employees_in_board: Optional[int] = None

    households_residential: Optional[int] = None
    households_shops_offices: Optional[int] = None
    households_open_plots: Optional[int] = None

    birth_registration_per_year: Optional[int] = None
    birth_certificate_per_year: Optional[int] = None

    created_by_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
