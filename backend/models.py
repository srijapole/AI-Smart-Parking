from sqlalchemy import Column, Integer, String
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