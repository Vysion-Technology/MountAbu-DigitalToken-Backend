from typing import Optional
from pydantic import BaseModel, Field


class CityProfileCreate(BaseModel):
    area_sq_km: Optional[str] = Field(None)
    no_of_wards: Optional[int] = Field(None)
    ward_boundaries: Optional[str] = Field(None)
    population_estimate: Optional[int] = Field(None)
    rental_properties_of_corporation: Optional[int] = Field(None)
    number_of_slums: Optional[int] = Field(None)
    solid_waste_per_day: Optional[str] = Field(None)
    street_light_poles: Optional[int] = Field(None)
    employees_in_board: Optional[int] = Field(None)

    households_residential: Optional[int] = Field(None)
    households_shops_offices: Optional[int] = Field(None)
    households_open_plots: Optional[int] = Field(None)

    birth_registration_per_year: Optional[int] = Field(None)
    birth_certificate_per_year: Optional[int] = Field(None)


class CityProfilePut(BaseModel):
    area_sq_km: str
    no_of_wards: int
    ward_boundaries: str
    population_estimate: int
    rental_properties_of_corporation: int
    number_of_slums: int
    solid_waste_per_day: str
    street_light_poles: int
    employees_in_board: int

    households_residential: int
    households_shops_offices: int
    households_open_plots: int

    birth_registration_per_year: int
    birth_certificate_per_year: int
