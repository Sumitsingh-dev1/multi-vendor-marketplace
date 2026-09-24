from pydantic import BaseModel


class AddressCreate(BaseModel):
    label: str
    latitude: float
    longitude: float
    address_line: str
    city: str
    state: str
    postal_code: str


class AddressUpdate(BaseModel):
    label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


class AddressResponse(BaseModel):
    id: int
    label: str
    latitude: float
    longitude: float
    address_line: str
    city: str
    state: str
    postal_code: str