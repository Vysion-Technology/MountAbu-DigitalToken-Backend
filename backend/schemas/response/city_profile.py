from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CityProfileResponse(BaseModel):
    id: int

    area_sq_km: Optional[str]
    no_of_wards: Optional[int]
    ward_boundaries: Optional[str]
    population_estimate: Optional[int]
    rental_properties_of_corporation: Optional[int]
    number_of_slums: Optional[int]
    solid_waste_per_day: Optional[str]
    street_light_poles: Optional[int]
    employees_in_board: Optional[int]

    households_residential: Optional[int]
    households_shops_offices: Optional[int]
    households_open_plots: Optional[int]

    birth_registration_per_year: Optional[int]
    birth_certificate_per_year: Optional[int]

    created_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
