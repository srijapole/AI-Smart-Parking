from sqlalchemy import Column, Integer, String, Float, ForeignKey
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    location = Column(String, nullable=False)
    vehicle = Column(String, nullable=False)
    booking_type = Column(String, nullable=False)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    slot = Column(String, nullable=False)
    status = Column(String, default="Reserved")


# Parking Vehicle Registration
class VehicleRegistration(Base):
    __tablename__ = "vehicle_registrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_number = Column(String, unique=True, nullable=False)
    vehicle_type = Column(String, nullable=False)
    owner_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    status = Column(String, default="Active")


# Pricing Management
class ParkingPricing(Base):
    __tablename__ = "parking_pricing"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_type = Column(String, unique=True, nullable=False)
    hourly_rate = Column(Float, nullable=False)
    daily_rate = Column(Float, nullable=False)


# Payment Management
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)
    payment_status = Column(String, default="Pending")
    transaction_id = Column(String, nullable=True)