from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)   # NULL 可。非NULLなら一意
    tel = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    reservations = relationship("Reservation", back_populates="user", cascade="all, delete-orphan")

class BookingSpot(Base):
    __tablename__ = "booking_spots"
    booking_spot_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    url = Column(String)
    email = Column(String, unique=True)   # NULL 可。非NULLなら一意
    tel = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    plans = relationship("Plan", back_populates="booking_spot", cascade="all, delete-orphan")

class Plan(Base):
    __tablename__ = "plans"
    plan_id = Column(Integer, primary_key=True)
    booking_spot_id = Column(Integer, ForeignKey("booking_spots.booking_spot_id"), nullable=False)
    name = Column(String, nullable=False)             # 例: プランA
    description = Column(String)
    price_yen = Column(Integer, nullable=False, default=0)
    default_duration_min = Column(Integer, nullable=False, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)

    booking_spot = relationship("BookingSpot", back_populates="plans")
    reservations = relationship("Reservation", back_populates="plan", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("booking_spot_id", "name", name="uq_plan_spot_name"),
    )

class Reservation(Base):
    __tablename__ = "reservations"
    reservation_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.plan_id"), nullable=False)
    start_datetime = Column(DateTime, nullable=False)   # すべてUTCで保存推奨
    end_datetime = Column(DateTime, nullable=False)
    note = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reservations")
    plan = relationship("Plan", back_populates="reservations")
