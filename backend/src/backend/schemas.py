
from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

UserType = Literal["employer", "client", "visitor"]
VehicleType = Literal["car", "bike"]


# -------------------------
# Authentication schemas
# -------------------------

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    mobile: str = Field(pattern=r"^[0-9]{10}$")
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    license_number: str | None = Field(default=None, max_length=30)
    dob: date | None = None
    user_type: UserType = "visitor"

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters")
        return value

    @field_validator("mobile")
    @classmethod
    def normalize_mobile(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class UserResponse(BaseModel):
    id: int
    full_name: str
    mobile: str
    email: EmailStr
    license_number: str | None
    dob: date | None
    user_type: UserType
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# -------------------------
# Vehicle schemas
# -------------------------

class VehicleCreateRequest(BaseModel):
    vehicle_number: str = Field(min_length=4, max_length=20)
    vehicle_type: VehicleType
    vehicle_model: str | None = Field(default=None, max_length=50)

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle_number(cls, value: str) -> str:
        return value.strip().upper()


class VehicleResponse(BaseModel):
    id: int
    user_id: int
    vehicle_number: str
    vehicle_type: VehicleType
    vehicle_model: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VehicleUpdateRequest(BaseModel):
    vehicle_number: str | None = Field(
        default=None,
        min_length=4,
        max_length=20,
    )
    vehicle_type: VehicleType | None = None
    vehicle_model: str | None = Field(
        default=None,
        max_length=50,
    )

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle_number(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            return value.strip().upper()
        return value

    
# -------------------------
# Parking location schemas
# -------------------------

class ParkingLocationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    building_number: str | None = Field(default=None, max_length=30)
    street: str = Field(min_length=2, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(pattern=r"^[0-9]{6}$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    description: str | None = None

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be provided together"
            )
        return self


class ParkingLocationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    building_number: str | None = Field(default=None, max_length=30)
    street: str | None = Field(default=None, min_length=2, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    pincode: str | None = Field(default=None, pattern=r"^[0-9]{6}$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    description: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be provided together"
            )
        return self


class ParkingLocationResponse(BaseModel):
    id: int
    name: str
    building_number: str | None
    street: str
    city: str
    state: str
    pincode: str
    latitude: float | None
    longitude: float | None
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

