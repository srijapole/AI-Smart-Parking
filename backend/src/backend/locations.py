
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import ParkingLocation, User
from backend.schemas import (
    ParkingLocationCreateRequest,
    ParkingLocationResponse,
    ParkingLocationUpdateRequest,
)


router = APIRouter(
    prefix="/api/v1/locations",
    tags=["Parking Locations"],
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=ParkingLocationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_location(
    data: ParkingLocationCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    location = ParkingLocation(**data.model_dump())

    db.add(location)
    db.commit()
    db.refresh(location)

    return location


@router.get(
    "",
    response_model=list[ParkingLocationResponse],
)
def get_locations(
    db: DbSession,
    current_user: CurrentUser,
):
    statement = (
        select(ParkingLocation)
        .where(ParkingLocation.is_active.is_(True))
        .order_by(ParkingLocation.id)
    )

    return db.scalars(statement).all()


@router.get(
    "/{location_id}",
    response_model=ParkingLocationResponse,
)
def get_location(
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    location = db.get(ParkingLocation, location_id)

    if location is None or not location.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking location not found",
        )

    return location


@router.patch(
    "/{location_id}",
    response_model=ParkingLocationResponse,
)
def update_location(
    location_id: int,
    data: ParkingLocationUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    location = db.get(ParkingLocation, location_id)

    if location is None or not location.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking location not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    for field, value in update_data.items():
        setattr(location, field, value)

    db.commit()
    db.refresh(location)

    return location


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_location(
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    location = db.get(ParkingLocation, location_id)

    if location is None or not location.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking location not found",
        )

    location.is_active = False

    db.commit()

    return None
