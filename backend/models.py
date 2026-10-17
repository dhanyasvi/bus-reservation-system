from sqlalchemy import Column, Integer, String, Float, DateTime, func
from database import Base

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    passenger_name = Column(String(80), nullable=False)
    source = Column(String(40), nullable=False)
    destination = Column(String(40), nullable=False)
    seat_no = Column(Integer, unique=True, nullable=True)
    status = Column(String(20), nullable=False, default="CONFIRMED")
    fare_amount = Column(Float, nullable=False, default=750.00)
    payment_status = Column(String(20), nullable=False, default="PAID")
    refund_amount = Column(Float, nullable=True)
    transaction_id = Column(String(64), nullable=True)
    user_id = Column(String(80), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    bus_number = Column(String(20), nullable=False)
    source = Column(String(40), nullable=False)
    destination = Column(String(40), nullable=False)
    departure_time = Column(String(20), nullable=False)
    arrival_time = Column(String(20), nullable=False)
    bus_type = Column(String(40), nullable=False, default="AC Semi-Sleeper")
    fare = Column(Float, nullable=False, default=750.00)
    total_seats = Column(Integer, nullable=False, default=40)
