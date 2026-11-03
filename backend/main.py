from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from db import engine, Base, SessionLocal
import models

# Create FastAPI application
app = FastAPI(title="AI Smart Parking API")

# Create database tables
Base.metadata.create_all(bind=engine)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Parking capacities
CAPACITIES = {
    "Car": 10,
    "Bike": 15,
    "Cycle": 5
}


# Request Models
class RegisterUser(BaseModel):
    name: str
    email: str
    password: str


class LoginUser(BaseModel):
    email: str
    password: str


class CreateReservation(BaseModel):
    user_id: int
    location: str
    vehicle: str
    booking_type: str
    date: str
    time: str


# Home API
@app.get("/")
def home():
    return {
        "message": "AI Smart Parking Backend is running!"
    }


# Database Connection Test
@app.get("/test-db")
def test_db():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "message": "Neon Database Connected Successfully!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Registration API
@app.post("/register")
def register(user: RegisterUser):
    db: Session = SessionLocal()

    try:
        existing_user = db.query(models.User).filter(
            models.User.email == user.email.lower()
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        new_user = models.User(
            name=user.name,
            email=user.email.lower(),
            password=user.password
        )

        db.add(new_user)
        db.commit()

        return {"message": "Registration successful"}

    finally:
        db.close()


# Login API
@app.post("/login")
def login(user: LoginUser):
    db: Session = SessionLocal()

    try:
        existing_user = db.query(models.User).filter(
            models.User.email == user.email.lower(),
            models.User.password == user.password
        ).first()

        if not existing_user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        return {
            "message": "Login successful",
            "user_id": existing_user.id,
            "name": existing_user.name,
            "email": existing_user.email
        }

    finally:
        db.close()


# Parking Slots API
@app.get("/parking/slots")
def parking_slots():
    return {
        "total_slots": 30,
        "car_slots": 10,
        "bike_slots": 15,
        "cycle_slots": 5
    }


# Parking Availability API
@app.get("/parking/availability")
def availability():
    db: Session = SessionLocal()

    try:
        result = {}

        for vehicle, capacity in CAPACITIES.items():
            active = db.query(models.Reservation).filter(
                models.Reservation.vehicle == vehicle,
                models.Reservation.status.in_(
                    ["Reserved", "Occupied"]
                )
            ).all()

            occupied = sum(
                1 for booking in active
                if booking.status == "Occupied"
            )

            reserved = sum(
                1 for booking in active
                if booking.status == "Reserved"
            )

            result[vehicle.lower()] = {
                "total": capacity,
                "occupied": occupied,
                "reserved": reserved,
                "available": capacity - occupied - reserved
            }

        total_available = sum(
            item["available"] for item in result.values()
        )

        total_occupied = sum(
            item["occupied"] for item in result.values()
        )

        total_reserved = sum(
            item["reserved"] for item in result.values()
        )

        return {
            "total": 30,
            "available": total_available,
            "occupied": total_occupied,
            "reserved": total_reserved,
            "vehicles": result
        }

    finally:
        db.close()


# Book Parking API
@app.post("/reservations")
def book_parking(booking: CreateReservation):
    db: Session = SessionLocal()

    try:
        user = db.query(models.User).filter(
            models.User.id == booking.user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if booking.vehicle not in CAPACITIES:
            raise HTTPException(
                status_code=400,
                detail="Invalid vehicle type"
            )

        active_bookings = db.query(
            models.Reservation
        ).filter(
            models.Reservation.vehicle == booking.vehicle,
            models.Reservation.status.in_(
                ["Reserved", "Occupied"]
            )
        ).all()

        capacity = CAPACITIES[booking.vehicle]

        if len(active_bookings) >= capacity:
            raise HTTPException(
                status_code=400,
                detail="No available parking slots"
            )

        used_slots = {
            item.slot for item in active_bookings
        }

        slot_number = next(
            number for number in range(1, capacity + 1)
            if f"{booking.vehicle}-{number}" not in used_slots
        )

        slot = f"{booking.vehicle}-{slot_number}"

        status = (
            "Occupied"
            if "walk" in booking.booking_type.lower()
            else "Reserved"
        )

        new_booking = models.Reservation(
            user_id=booking.user_id,
            location=booking.location,
            vehicle=booking.vehicle,
            booking_type=booking.booking_type,
            date=booking.date,
            time=booking.time,
            slot=slot,
            status=status
        )

        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        return {
            "message": "Parking booked successfully",
            "booking_id": new_booking.id,
            "slot": new_booking.slot,
            "status": new_booking.status
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


# My Reservations API
@app.get("/reservations")
def reservations(user_id: int):
    db: Session = SessionLocal()

    try:
        bookings = db.query(
            models.Reservation
        ).filter(
            models.Reservation.user_id == user_id
        ).order_by(
            models.Reservation.id.desc()
        ).all()

        return {
            "reservations": [
                {
                    "id": item.id,
                    "user_id": item.user_id,
                    "location": item.location,
                    "vehicle": item.vehicle,
                    "booking_type": item.booking_type,
                    "date": item.date,
                    "time": item.time,
                    "slot": item.slot,
                    "status": item.status
                }
                for item in bookings
            ]
        }

    finally:
        db.close()


# Cancel Reservation API
@app.delete("/reservations/{reservation_id}")
def cancel_reservation(
    reservation_id: int,
    user_id: int
):
    db: Session = SessionLocal()

    try:
        booking = db.query(
            models.Reservation
        ).filter(
            models.Reservation.id == reservation_id,
            models.Reservation.user_id == user_id
        ).first()

        if not booking:
            raise HTTPException(
                status_code=404,
                detail="Reservation not found"
            )

        if booking.status == "Cancelled":
            raise HTTPException(
                status_code=400,
                detail="Reservation already cancelled"
            )

        booking.status = "Cancelled"

        db.commit()

        return {
            "message": "Reservation cancelled successfully",
            "booking_id": reservation_id
        }

    finally:
        db.close()