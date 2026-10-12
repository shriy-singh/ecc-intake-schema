"""One Pydantic model per routine ECC request type.

Every field is required: no field has a default, so a report missing any
field fails validation and must not be saved. ``license_plate`` is the one
field whose *value* may be ``None`` (the resident could not read the plate),
but the key itself must still be supplied explicitly.
"""

import re
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints, field_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _RequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location: NonEmptyStr
    incident_observed_at: AwareDatetime
    callback_phone: NonEmptyStr

    @field_validator("callback_phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("callback_phone must be a 10-digit phone number")
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


class NoiseComplaint(_RequestBase):
    request_type: Literal["noise_complaint"]
    noise_source: NonEmptyStr


class IllegallyParkedVehicle(_RequestBase):
    request_type: Literal["illegally_parked_vehicle"]
    vehicle_description: NonEmptyStr
    # nullable: ECC-T-010, ECC-T-025, ECC-T-037 are complete routine chats with no readable plate
    license_plate: NonEmptyStr | None
    blocking_driveway: bool

    @field_validator("license_plate")
    @classmethod
    def normalize_plate(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class Pothole(_RequestBase):
    request_type: Literal["pothole"]
    pothole_size: NonEmptyStr
    hazard_to_traffic: bool


ROUTINE_REQUEST_MODELS: dict[str, type[_RequestBase]] = {
    "noise_complaint": NoiseComplaint,
    "illegally_parked_vehicle": IllegallyParkedVehicle,
    "pothole": Pothole,
}
