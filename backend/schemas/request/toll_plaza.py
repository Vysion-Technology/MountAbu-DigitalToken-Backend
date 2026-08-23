from pydantic import BaseModel, Field

class TollPlazaVerifyRequest(BaseModel):
    transport_code: str = Field(..., description="Cryptographically signed transport code string")
    vehicle_number: str = Field(..., description="Vehicle registration number")
