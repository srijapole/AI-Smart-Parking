from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import (
    User,
    Vehicle,
    ParkingLocation,
    ParkingSlot,
    Reservation,
)
from backend.schemas import (
    ReservationCreateRequest,
    ReservationResponse,
)

router = APIRouter(
    prefix="/api/v1/reservations",
    tags=["Reservations"],
)


@router.post(
    "",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reservation(
    reservation_data: ReservationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Check whether the vehicle belongs to the logged-in user
    vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.id == reservation_data.vehicle_id,
            Vehicle.user_id == current_user.id,
        )
    )

    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found or does not belong to you",
        )

    # 2. Check whether the parking location exists and is active
    location = db.scalar(
        select(ParkingLocation).where(
            ParkingLocation.id == reservation_data.location_id,
            ParkingLocation.is_active.is_(True),
        )
    )

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking location not found or inactive",
        )

    # 3. Check whether the slot belongs to the selected location
    # and is active
    slot = db.scalar(
        select(ParkingSlot).where(
            ParkingSlot.id == reservation_data.slot_id,
            ParkingSlot.location_id == reservation_data.location_id,
            ParkingSlot.is_active.is_(True),
        )
    )

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking slot not found or inactive at this location",
        )

    # 4. Check whether the vehicle type matches the slot
    if vehicle.vehicle_type.lower() != slot.vehicle_type.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle type does not match the parking slot",
        )

    # 5. Check whether the requested time is in the future
    now = datetime.now(timezone.utc)

    if reservation_data.start_time.astimezone(timezone.utc) <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation start time must be in the future",
        )

    # 6. Check for overlapping confirmed reservations
    overlapping_reservation = db.scalar(
        select(Reservation).where(
            Reservation.slot_id == reservation_data.slot_id,
            Reservation.status == "confirmed",
            Reservation.start_time < reservation_data.end_time,
            Reservation.end_time > reservation_data.start_time,
        )
    )

    if overlapping_reservation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This parking slot is already reserved for the selected time",
        )

    # 7. Create the reservation
    new_reservation = Reservation(
        user_id=current_user.id,
        vehicle_id=reservation_data.vehicle_id,
        location_id=reservation_data.location_id,
        slot_id=reservation_data.slot_id,
        start_time=reservation_data.start_time.astimezone(timezone.utc),
        end_time=reservation_data.end_time.astimezone(timezone.utc),
        status="confirmed",
    )
  

    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)

    return new_reservation

@router.get(
    "",
    response_model=list[ReservationResponse],
)
def get_my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reservations = db.scalars(
        select(Reservation)
        .where(Reservation.user_id == current_user.id)
        .order_by(Reservation.created_at.desc())
    ).all()

    return reservations

@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reservation = db.scalar(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id,
        )
    )

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    return reservation

@router.patch(
    "/{reservation_id}/cancel",
    response_model=ReservationResponse,
)
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reservation = db.scalar(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id,
        )
    )

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    if reservation.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only confirmed reservations can be cancelled",
        )

    reservation.status = "cancelled"

    db.commit()
    db.refresh(reservation)

    return reservation