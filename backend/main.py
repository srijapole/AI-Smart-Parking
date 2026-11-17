from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from db import engine, Base, SessionLocal
import models


app = FastAPI(
    title="AI Smart Parking API",
    description="Parking Registration, Pricing, Payments and Agentic AI",
    version="2.0"
)

# Create database tables
Base.metadata.create_all(bind=engine)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Parking Capacity
CAPACITIES = {
    "Car": 10,
    "Bike": 15,
    "Cycle": 5
}


# ---------------- REQUEST MODELS ----------------

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


class VehicleRegister(BaseModel):
    user_id: int
    vehicle_number: str
    vehicle_type: str
    owner_name: str
    phone: str


class PricingCreate(BaseModel):
    vehicle_type: str
    hourly_rate: float
    daily_rate: float


class PaymentCreate(BaseModel):
    user_id: int
    reservation_id: int
    amount: float
    payment_method: str


class AgentRequest(BaseModel):
    user_id: int
    location: str
    vehicle: str
    date: str
    time: str
    booking_type: str = "Online"


# ---------------- HOME API ----------------

@app.get("/", tags=["Home"])
def home():
    return {
        "message": "AI Smart Parking Backend is running!"
    }


# ---------------- DATABASE API ----------------

@app.get("/test-db", tags=["Database"])
def test_db():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "message": "Neon Database Connected Successfully!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- USER REGISTRATION ----------------

@app.post("/register", tags=["User Management"])
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


# ---------------- LOGIN ----------------

@app.post("/login", tags=["User Management"])
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


# ---------------- PARKING SLOTS ----------------

@app.get("/parking/slots", tags=["Parking"])
def parking_slots():

    return {
        "total_slots": 30,
        "car_slots": 10,
        "bike_slots": 15,
        "cycle_slots": 5
    }


# ---------------- PARKING AVAILABILITY ----------------

@app.get("/parking/availability", tags=["Parking"])
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
                1 for item in active
                if item.status == "Occupied"
            )

            reserved = sum(
                1 for item in active
                if item.status == "Reserved"
            )

            result[vehicle.lower()] = {
                "total": capacity,
                "occupied": occupied,
                "reserved": reserved,
                "available": max(
                    0, capacity - occupied - reserved
                )
            }

        return {
            "total": 30,
            "vehicles": result,
            "available": sum(
                item["available"] for item in result.values()
            )
        }

    finally:
        db.close()


# ---------------- BOOK PARKING ----------------

@app.post("/reservations", tags=["Reservations"])
def book_parking(booking: CreateReservation):

    db: Session = SessionLocal()

    try:
        user = db.query(models.User).filter(
            models.User.id == booking.user_id
        ).first()

        if not user:
            raise HTTPException(404, "User not found")

        if booking.vehicle not in CAPACITIES:
            raise HTTPException(400, "Invalid vehicle type")

        active = db.query(models.Reservation).filter(
            models.Reservation.vehicle == booking.vehicle,
            models.Reservation.date == booking.date,
            models.Reservation.status.in_(
                ["Reserved", "Occupied"]
            )
        ).all()

        capacity = CAPACITIES[booking.vehicle]

        if len(active) >= capacity:
            raise HTTPException(
                400, "No available parking slots"
            )

        used_slots = {item.slot for item in active}

        slot_number = next(
            (
                n for n in range(1, capacity + 1)
                if f"{booking.vehicle}-{n}" not in used_slots
            ),
            None
        )

        if slot_number is None:
            raise HTTPException(400, "No available slots")

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
        raise HTTPException(500, str(e))

    finally:
        db.close()


# ---------------- MY RESERVATIONS ----------------

@app.get("/reservations", tags=["Reservations"])
def reservations(user_id: int):

    db: Session = SessionLocal()

    try:
        bookings = db.query(models.Reservation).filter(
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


# ---------------- CANCEL RESERVATION ----------------

@app.delete(
    "/reservations/{reservation_id}",
    tags=["Reservations"]
)
def cancel_reservation(reservation_id: int, user_id: int):

    db: Session = SessionLocal()

    try:
        booking = db.query(models.Reservation).filter(
            models.Reservation.id == reservation_id,
            models.Reservation.user_id == user_id
        ).first()

        if not booking:
            raise HTTPException(404, "Reservation not found")

        if booking.status == "Cancelled":
            raise HTTPException(
                400, "Reservation already cancelled"
            )

        booking.status = "Cancelled"
        db.commit()

        return {
            "message": "Reservation cancelled successfully",
            "booking_id": reservation_id
        }

    finally:
        db.close()


# ==================================================
# 1. PARKING REGISTRATION
# ==================================================

@app.post("/parking/register", tags=["Parking Registration"])
def parking_register(data: VehicleRegister):

    db: Session = SessionLocal()

    try:
        user = db.query(models.User).filter(
            models.User.id == data.user_id
        ).first()

        if not user:
            raise HTTPException(404, "User not found")

        if data.vehicle_type not in CAPACITIES:
            raise HTTPException(400, "Invalid vehicle type")

        existing = db.query(
            models.VehicleRegistration
        ).filter(
            models.VehicleRegistration.vehicle_number ==
            data.vehicle_number.upper()
        ).first()

        if existing:
            raise HTTPException(
                400, "Vehicle already registered"
            )

        vehicle = models.VehicleRegistration(
            user_id=data.user_id,
            vehicle_number=data.vehicle_number.upper(),
            vehicle_type=data.vehicle_type,
            owner_name=data.owner_name,
            phone=data.phone,
            status="Active"
        )

        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)

        return {
            "message": "Vehicle registered successfully",
            "registration_id": vehicle.id,
            "vehicle_number": vehicle.vehicle_number,
            "status": vehicle.status
        }

    finally:
        db.close()


@app.get("/parking/registrations", tags=["Parking Registration"])
def get_registrations(user_id: int):

    db: Session = SessionLocal()

    try:
        vehicles = db.query(
            models.VehicleRegistration
        ).filter(
            models.VehicleRegistration.user_id == user_id
        ).all()

        return {
            "registrations": [
                {
                    "id": v.id,
                    "vehicle_number": v.vehicle_number,
                    "vehicle_type": v.vehicle_type,
                    "owner_name": v.owner_name,
                    "phone": v.phone,
                    "status": v.status
                }
                for v in vehicles
            ]
        }

    finally:
        db.close()


# ==================================================
# 2. PRICING MANAGEMENT
# ==================================================

@app.post("/pricing", tags=["Pricing Management"])
def create_pricing(data: PricingCreate):

    db: Session = SessionLocal()

    try:
        if data.vehicle_type not in CAPACITIES:
            raise HTTPException(400, "Invalid vehicle type")

        if data.hourly_rate < 0 or data.daily_rate < 0:
            raise HTTPException(400, "Price cannot be negative")

        existing = db.query(models.ParkingPricing).filter(
            models.ParkingPricing.vehicle_type == data.vehicle_type
        ).first()

        if existing:
            existing.hourly_rate = data.hourly_rate
            existing.daily_rate = data.daily_rate
            message = "Pricing updated successfully"
        else:
            pricing = models.ParkingPricing(
                vehicle_type=data.vehicle_type,
                hourly_rate=data.hourly_rate,
                daily_rate=data.daily_rate
            )
            db.add(pricing)
            message = "Pricing created successfully"

        db.commit()

        return {"message": message}

    finally:
        db.close()


@app.get("/pricing", tags=["Pricing Management"])
def get_pricing():

    db: Session = SessionLocal()

    try:
        prices = db.query(models.ParkingPricing).all()

        return {
            "pricing": [
                {
                    "vehicle_type": p.vehicle_type,
                    "hourly_rate": p.hourly_rate,
                    "daily_rate": p.daily_rate
                }
                for p in prices
            ]
        }

    finally:
        db.close()


@app.get("/pricing/calculate", tags=["Pricing Management"])
def calculate_price(
    vehicle_type: str,
    hours: float
):

    db: Session = SessionLocal()

    try:
        if hours <= 0:
            raise HTTPException(400, "Hours must be positive")

        pricing = db.query(models.ParkingPricing).filter(
            models.ParkingPricing.vehicle_type == vehicle_type
        ).first()

        if not pricing:
            raise HTTPException(404, "Pricing not found")

        amount = hours * pricing.hourly_rate

        return {
            "vehicle_type": vehicle_type,
            "hours": hours,
            "hourly_rate": pricing.hourly_rate,
            "total_amount": round(amount, 2),
            "currency": "INR"
        }

    finally:
        db.close()


# ==================================================
# 3. PAYMENT MANAGEMENT
# ==================================================

@app.post("/payments", tags=["Payments"])
def create_payment(data: PaymentCreate):

    db: Session = SessionLocal()

    try:
        if data.amount <= 0:
            raise HTTPException(400, "Invalid payment amount")

        reservation = db.query(models.Reservation).filter(
            models.Reservation.id == data.reservation_id,
            models.Reservation.user_id == data.user_id
        ).first()

        if not reservation:
            raise HTTPException(404, "Reservation not found")

        if reservation.status == "Cancelled":
            raise HTTPException(
                400, "Cannot pay for a cancelled reservation"
            )

        payment = models.Payment(
            user_id=data.user_id,
            reservation_id=data.reservation_id,
            amount=data.amount,
            payment_method=data.payment_method,
            payment_status="Pending",
            transaction_id=None
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {
            "message": "Payment record created",
            "payment_id": payment.id,
            "amount": payment.amount,
            "payment_status": payment.payment_status
        }

    finally:
        db.close()


@app.get("/payments", tags=["Payments"])
def get_payments(user_id: int):

    db: Session = SessionLocal()

    try:
        payments = db.query(models.Payment).filter(
            models.Payment.user_id == user_id
        ).all()

        return {
            "payments": [
                {
                    "payment_id": p.id,
                    "reservation_id": p.reservation_id,
                    "amount": p.amount,
                    "method": p.payment_method,
                    "status": p.payment_status,
                    "transaction_id": p.transaction_id
                }
                for p in payments
            ]
        }

    finally:
        db.close()


# ==================================================
# 4. AI OCCUPANCY AND DEMAND PREDICTION
# ==================================================

@app.get("/ai/prediction", tags=["AI Prediction"])
def ai_prediction():

    db: Session = SessionLocal()

    try:
        predictions = {}

        for vehicle, capacity in CAPACITIES.items():

            active = db.query(models.Reservation).filter(
                models.Reservation.vehicle == vehicle,
                models.Reservation.status.in_(
                    ["Reserved", "Occupied"]
                )
            ).count()

            occupancy = (active / capacity) * 100

            if occupancy >= 80:
                demand = "High"
                recommendation = "Increase parking price"
            elif occupancy >= 50:
                demand = "Medium"
                recommendation = "Maintain current pricing"
            else:
                demand = "Low"
                recommendation = "Offer parking discounts"

            predictions[vehicle] = {
                "capacity": capacity,
                "current_bookings": active,
                "occupancy_percentage": round(occupancy, 2),
                "predicted_demand": demand,
                "recommendation": recommendation
            }

        return {
            "message": "AI parking demand analysis completed",
            "predictions": predictions
        }

    finally:
        db.close()


# ==================================================
# 5. AGENTIC AI WORKFLOW
# ==================================================

@app.post("/ai/agent-workflow", tags=["Agentic AI Workflow"])
def agent_workflow(data: AgentRequest):

    db: Session = SessionLocal()

    try:
        user = db.query(models.User).filter(
            models.User.id == data.user_id
        ).first()

        if not user:
            raise HTTPException(404, "User not found")

        if data.vehicle not in CAPACITIES:
            raise HTTPException(400, "Invalid vehicle type")

        # Agent 1: Check parking availability
        active = db.query(models.Reservation).filter(
            models.Reservation.vehicle == data.vehicle,
            models.Reservation.date == data.date,
            models.Reservation.status.in_(
                ["Reserved", "Occupied"]
            )
        ).all()

        capacity = CAPACITIES[data.vehicle]
        available = capacity - len(active)

        # Agent 2: Check pricing
        pricing = db.query(models.ParkingPricing).filter(
            models.ParkingPricing.vehicle_type == data.vehicle
        ).first()

        hourly_rate = (
            pricing.hourly_rate if pricing else 0
        )

        # Agent 3: Analyze demand
        occupancy = (len(active) / capacity) * 100

        if occupancy >= 80:
            demand = "High"
        elif occupancy >= 50:
            demand = "Medium"
        else:
            demand = "Low"

        # Agent 4: Generate recommendation
        if available > 0:
            recommendation = (
                f"Parking is available for {data.vehicle}. "
                "You can proceed with booking."
            )
            action = "Booking recommended"
        else:
            recommendation = (
                "Parking is full. Please try another time."
            )
            action = "Booking not recommended"

        return {
            "workflow": "AI Smart Parking Agent Workflow",
            "steps": {
                "user_validation": "Completed",
                "availability_check": "Completed",
                "pricing_check": "Completed",
                "demand_analysis": "Completed",
                "recommendation": "Completed"
            },
            "user": user.name,
            "location": data.location,
            "vehicle": data.vehicle,
            "date": data.date,
            "time": data.time,
            "available_slots": max(0, available),
            "hourly_rate": hourly_rate,
            "demand": demand,
            "recommendation": recommendation,
            "action": action
        }

    finally:
        db.close()