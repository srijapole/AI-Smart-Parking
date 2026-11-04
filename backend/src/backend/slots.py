
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import ParkingLocation, ParkingSlot, User
from backend.schemas import (
    ParkingSlotCreateRequest,
    ParkingSlotResponse,
    ParkingSlotUpdateRequest,
)


router = APIRouter(
    prefix="/api/v1/slots",
    tags=["Parking Slots"],
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=ParkingSlotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_slot(
    data: ParkingSlotCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    location = db.get(ParkingLocation, data.location_id)

    if location is None or not location.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active parking location not found",
        )

    slot = ParkingSlot(**data.model_dump())

    db.add(slot)

    try:
        db.commit()
        db.refresh(slot)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A slot with this number already exists in this location",
        )

    return slot


@router.get(
    "",
    response_model=list[ParkingSlotResponse],
)
def get_slots(
    db: DbSession,
    current_user: CurrentUser,
    location_id: Annotated[int | None, Query(gt=0)] = None,
):
    statement = select(ParkingSlot).where(
        ParkingSlot.is_active.is_(True)
    )

    if location_id is not None:
        statement = statement.where(
            ParkingSlot.location_id == location_id
        )

    statement = statement.order_by(ParkingSlot.id)

    return db.scalars(statement).all()


@router.get(
    "/{slot_id}",
    response_model=ParkingSlotResponse,
)
def get_slot(
    slot_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    slot = db.get(ParkingSlot, slot_id)

    if slot is None or not slot.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking slot not found",
        )

    return slot


@router.patch(
    "/{slot_id}",
    response_model=ParkingSlotResponse,
)
def update_slot(
    slot_id: int,
    data: ParkingSlotUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    slot = db.get(ParkingSlot, slot_id)

    if slot is None or not slot.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking slot not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    for field, value in update_data.items():
        setattr(slot, field, value)

    try:
        db.commit()
        db.refresh(slot)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A slot with this number already exists in this location",
        )

    return slot


@router.delete(
    "/{slot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_slot(
    slot_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    slot = db.get(ParkingSlot, slot_id)

    if slot is None or not slot.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking slot not found",
        )

    slot.is_active = False
    db.commit()

    return None
