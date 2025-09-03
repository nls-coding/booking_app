from .database import Base, engine, SessionLocal
from .models import User, BookingSpot, Plan
from sqlalchemy import select

def seed():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        spot = db.execute(select(BookingSpot)).scalar()
        if not spot:
            spot = BookingSpot(name="デフォルトスポット", address="東京都...", url="https://example.com")
            db.add(spot); db.commit(); db.refresh(spot)

        if not db.execute(select(Plan).where(Plan.booking_spot_id==spot.booking_spot_id)).first():
            db.add_all([
                Plan(booking_spot_id=spot.booking_spot_id, name="プランA", description="ベーシック", price_yen=8000, default_duration_min=60),
                Plan(booking_spot_id=spot.booking_spot_id, name="プランB", description="スタンダード", price_yen=12000, default_duration_min=90),
            ])
            db.commit()

        if not db.execute(select(User)).first():
            db.add(User(name="山田太郎", email="taro@example.com", tel="090-xxxx-xxxx"))
            db.commit()
    print("Seed completed.")

if __name__ == "__main__":
    seed()
