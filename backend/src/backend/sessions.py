from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import (
    User,
    Vehicle,
    ParkingLocation,
    ParkingSlot,
    Reservation,
    ParkingSession,
)
from backend.schemas import (
    ParkingSessionCheckInRequest,
    ParkingSessionResponse,
)

router = APIRouter(
    prefix="/api/v1/sessions",
    tags=["Parking Sessions"],
)

@router.post(
    "/check-in",
    response_model=ParkingSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def check_in(
    check_in_data: ParkingSessionCheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Check whether the vehicle belongs to the logged-in user
    vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.id == check_in_data.vehicle_id,
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
            ParkingLocation.id == check_in_data.location_id,
            ParkingLocation.is_active.is_(True),
        )
    )

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking location not found or inactive",
        )

    # 3. Lock the selected slot while processing check-in
    slot = db.scalar(
        select(ParkingSlot)
        .where(
            ParkingSlot.id == check_in_data.slot_id,
            ParkingSlot.location_id == check_in_data.location_id,
            ParkingSlot.is_active.is_(True),
        )
        .with_for_update()
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

    # 5. Get the current time in UTC
    now = datetime.now(timezone.utc)

        # 6. Check whether the slot already has an active session
    active_slot_session = db.scalar(
        select(ParkingSession).where(
            ParkingSession.slot_id == slot.id,
            ParkingSession.status == "active",
        )
    )

    if active_slot_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This parking slot is already occupied",
        )

    # 7. Check whether the vehicle already has an active session
    active_vehicle_session = db.scalar(
        select(ParkingSession).where(
            ParkingSession.vehicle_id == vehicle.id,
            ParkingSession.status == "active",
        )
    )

    if active_vehicle_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This vehicle already has an active parking session",
        )

        # 8. Validate reservation check-in
    reservation = None

    if check_in_data.reservation_id is not None:
        reservation = db.scalar(
            select(Reservation)
            .where(
                Reservation.id == check_in_data.reservation_id,
                Reservation.user_id == current_user.id,
            )
            .with_for_update()
        )

        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found",
            )

        # Check whether reservation details match the check-in
        if (
            reservation.vehicle_id != vehicle.id
            or reservation.location_id != location.id
            or reservation.slot_id != slot.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle, location or slot does not match the reservation",
            )

        # Check whether the reservation is still confirmed
        if reservation.status != "confirmed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reservation is no longer active",
            )

        # Calculate the 15-minute grace period
        reservation_start = reservation.start_time.astimezone(
            timezone.utc
        )
        grace_deadline = reservation_start + timedelta(minutes=15)

        # Cancel missed reservations
        if now > grace_deadline:
            reservation.status = "cancelled"
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-in window expired. Reservation has been cancelled",
            )

                # Do not allow check-in after the reservation has ended
        reservation_end = reservation.end_time.astimezone(
            timezone.utc
        )

        if now >= reservation_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The reservation has already ended",
            )

        # Do not allow check-in before the reservation starts
        if now < reservation_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-in is allowed only from the reservation start time",
            )

            # 9. Validate walk-in check-in
    if reservation is None:
        expected_exit = check_in_data.expected_exit_time.astimezone(
            timezone.utc
        )

        # Expected exit time must be in the future
        if expected_exit <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expected exit time must be in the future",
            )

        # Find confirmed reservations that have not ended yet
        upcoming_reservations = db.scalars(
            select(Reservation)
            .where(
                Reservation.slot_id == slot.id,
                Reservation.status == "confirmed",
                Reservation.end_time > now,
            )
            .order_by(Reservation.start_time.asc())
        ).all()
        # Cancel reservations whose 15-minute check-in window has expired
        valid_reservations = []
        for item in upcoming_reservations:
            reservation_start = item.start_time.astimezone(
                timezone.utc
            )
            grace_deadline = reservation_start + timedelta(minutes=15)

            if now > grace_deadline:
                item.status = "cancelled"
                continue

            valid_reservations.append(item)

        if valid_reservations:
            next_reservation = valid_reservations[0]

            # The slot must be protected 15 minutes before the next booking
            protected_check_in_time = (
                next_reservation.start_time.astimezone(timezone.utc)
                - timedelta(minutes=15)
            )

            if now >= protected_check_in_time:
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "This slot is reserved for an upcoming booking "
                        "and is no longer available for walk-in parking"
                    ),
                )

            if expected_exit > protected_check_in_time:
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Expected exit time overlaps with the next "
                        "reservation's protected check-in period"
                    ),
                )

    # 10. Create the parking session
    new_session = ParkingSession(
        user_id=current_user.id,
        vehicle_id=vehicle.id,
        location_id=location.id,
        slot_id=slot.id,
        reservation_id=reservation.id if reservation else None,
        entry_time=now,
        status="active",
    )

    try:
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This vehicle or parking slot already has "
                "an active parking session"
            ),
        )

    return new_session

@router.patch(
    "/{session_id}/check-out",
    response_model=ParkingSessionResponse,
)
def check_out(
    session_id: int,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Find the session belonging to the logged-in user
    parking_session = db.scalar(
        select(ParkingSession).where(
            ParkingSession.id == session_id,
            ParkingSession.user_id == current_user.id,
        )
    )

    if not parking_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking session not found",
        )

    # 2. Check whether the session is still active
    if parking_session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This parking session has already been completed",
        )

    # 3. Record the checkout time
    
    parking_session.exit_time = datetime.now(timezone.utc)
    parking_session.status = "completed"
   
    

    # 4. Save the changes
    db.commit()
    db.refresh(parking_session)

    return parking_session

@router.get(
    "",
    response_model=list[ParkingSessionResponse],
)
def get_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.scalars(
        select(ParkingSession)
        .where(ParkingSession.user_id == current_user.id)
        .order_by(ParkingSession.created_at.desc())
    ).all()

    return sessions

@router.get(
    "/{session_id}",
    response_model=ParkingSessionResponse,
)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parking_session = db.scalar(
        select(ParkingSession).where(
            ParkingSession.id == session_id,
            ParkingSession.user_id == current_user.id,
        )
    )

    if not parking_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking session not found",
        )

    return parking_session