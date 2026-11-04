
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import User, Vehicle
from backend.schemas import (
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateRequest,
)


router = APIRouter(
    prefix="/api/v1/vehicles",
    tags=["Vehicles"],
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    data: VehicleCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    vehicle = Vehicle(
        user_id=current_user.id,
        vehicle_number=data.vehicle_number,
        vehicle_type=data.vehicle_type,
        vehicle_model=data.vehicle_model,
    )

    db.add(vehicle)

    try:
        db.commit()
        db.refresh(vehicle)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This vehicle number is already registered",
        ) from None

    return vehicle


@router.get(
    "",
    response_model=list[VehicleResponse],
)
def get_my_vehicles(
    db: DbSession,
    current_user: CurrentUser,
):
    statement = select(Vehicle).where(
        Vehicle.user_id == current_user.id
    )

    return db.scalars(statement).all()


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
)
def get_vehicle(
    vehicle_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.user_id == current_user.id,
        )
    )

    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    return vehicle


@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
)
def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.user_id == current_user.id,
        )
    )

    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    for field, value in update_data.items():
        setattr(vehicle, field, value)

    try:
        db.commit()
        db.refresh(vehicle)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This vehicle number is already registered",
        ) from None

    return vehicle


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vehicle(
    vehicle_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.user_id == current_user.id,
        )
    )

    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    db.delete(vehicle)
    db.commit()

    return None
