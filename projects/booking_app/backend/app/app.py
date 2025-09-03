from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from dateutil import parser, tz
from .database import Base, engine, SessionLocal
from .models import User, BookingSpot, Plan, Reservation

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

Base.metadata.create_all(bind=engine)

def _parse_iso(dt_str: str) -> datetime:
    dt = parser.isoparse(dt_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz.UTC)
    return dt.astimezone(tz.UTC)

def _overlaps(db, plan_id: int, start_dt: datetime, end_dt: datetime, exclude_id=None) -> bool:
    q = select(Reservation).where(
        and_(
            Reservation.plan_id == plan_id,
            Reservation.start_datetime < end_dt,
            Reservation.end_datetime > start_dt
        )
    )
    if exclude_id is not None:
        q = q.where(Reservation.reservation_id != exclude_id)
    return db.execute(q).first() is not None

@app.get("/api/health")
def health():
    return {"ok": True}

# ---------- Users ----------
@app.post("/api/users")
def create_user():
    data = request.get_json(force=True)
    name = data.get("name")
    if not name:
        return jsonify({"error":{"code":"VALIDATION_ERROR","message":"name is required","details":{"field":"name","reason":"missing"}}}),400
    with SessionLocal() as db:
        u = User(name=name, email=data.get("email"), tel=data.get("tel"))
        db.add(u); db.commit(); db.refresh(u)
        return jsonify({
            "user_id": u.user_id, "name": u.name, "email": u.email, "tel": u.tel,
            "created_at": u.created_at.replace(tzinfo=tz.UTC).isoformat()
        }), 201

@app.get("/api/users")
def list_users():
    with SessionLocal() as db:
        rows = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
        return jsonify({"data":[{"user_id":u.user_id,"name":u.name,"email":u.email,"tel":u.tel} for u in rows],
                        "page":1,"per_page":len(rows),"total":len(rows)})

@app.get("/api/users/<int:user_id>")
def get_user(user_id: int):
    with SessionLocal() as db:
        u = db.get(User, user_id)
        if not u:
            return jsonify({"error":{"code":"NOT_FOUND","message":"user not found","details":{"user_id":user_id}}}),404
        return jsonify({"user_id":u.user_id,"name":u.name,"email":u.email,"tel":u.tel})

# ---------- Booking Spots ----------
@app.post("/api/booking_spots")
def create_spot():
    data = request.get_json(force=True)
    name = data.get("name")
    if not name:
        return jsonify({"error":{"code":"VALIDATION_ERROR","message":"name is required","details":{"field":"name","reason":"missing"}}}),400
    with SessionLocal() as db:
        s = BookingSpot(name=name, address=data.get("address"), url=data.get("url"),
                        email=data.get("email"), tel=data.get("tel"))
        db.add(s); db.commit(); db.refresh(s)
        return jsonify({"booking_spot_id":s.booking_spot_id,"name":s.name,"address":s.address,
                        "url":s.url,"email":s.email,"tel":s.tel}), 201

@app.get("/api/booking_spots")
def list_spots():
    with SessionLocal() as db:
        rows = db.execute(select(BookingSpot).order_by(BookingSpot.name.asc())).scalars().all()
        return jsonify({"data":[{"booking_spot_id":x.booking_spot_id,"name":x.name,"address":x.address} for x in rows],
                        "page":1,"per_page":len(rows),"total":len(rows)})

@app.get("/api/booking_spots/<int:spot_id>")
def get_spot(spot_id:int):
    with SessionLocal() as db:
        s = db.get(BookingSpot, spot_id)
        if not s:
            return jsonify({"error":{"code":"NOT_FOUND","message":"booking_spot not found","details":{"booking_spot_id":spot_id}}}),404
        return jsonify({"booking_spot_id":s.booking_spot_id,"name":s.name,"address":s.address,"url":s.url,"email":s.email,"tel":s.tel})

# ---------- Plans ----------
@app.post("/api/booking_spots/<int:spot_id>/plans")
def create_plan(spot_id:int):
    data = request.get_json(force=True)
    name = data.get("name")
    if not name:
        return jsonify({"error":{"code":"VALIDATION_ERROR","message":"name is required","details":{"field":"name","reason":"missing"}}}),400
    with SessionLocal() as db:
        spot = db.get(BookingSpot, spot_id)
        if not spot:
            return jsonify({"error":{"code":"NOT_FOUND","message":"booking_spot not found","details":{"booking_spot_id":spot_id}}}),404
        p = Plan(booking_spot_id=spot_id, name=name, description=data.get("description"),
                 price_yen=data.get("price_yen",0), default_duration_min=data.get("default_duration_min",60))
        db.add(p)
        try:
            db.commit()
        except Exception:
            db.rollback()
            return jsonify({"error":{"code":"DUPLICATE","message":"plan name duplicated in the spot"}}),409
        db.refresh(p)
        return jsonify({"plan_id":p.plan_id,"booking_spot_id":p.booking_spot_id,
                        "name":p.name,"price_yen":p.price_yen,"default_duration_min":p.default_duration_min}),201

@app.get("/api/booking_spots/<int:spot_id>/plans")
def list_plans_by_spot(spot_id:int):
    with SessionLocal() as db:
        rows = db.execute(select(Plan).where(Plan.booking_spot_id==spot_id).order_by(Plan.name.asc())).scalars().all()
        return jsonify({"data":[{"plan_id":p.plan_id,"name":p.name,"price_yen":p.price_yen} for p in rows]})

@app.get("/api/plans/<int:plan_id>")
def get_plan(plan_id:int):
    with SessionLocal() as db:
        p = db.get(Plan, plan_id)
        if not p:
            return jsonify({"error":{"code":"NOT_FOUND","message":"plan not found","details":{"plan_id":plan_id}}}),404
        return jsonify({"plan_id":p.plan_id,"booking_spot_id":p.booking_spot_id,"name":p.name,
                        "description":p.description,"price_yen":p.price_yen,"default_duration_min":p.default_duration_min})

# ---------- Reservations ----------
@app.post("/api/reservations")
def create_reservation():
    data = request.get_json(force=True)
    required = ["plan_id","start_datetime","end_datetime"]
    for k in required:
        if k not in data:
            return jsonify({"error":{"code":"VALIDATION_ERROR","message":f"{k} is required","details":{"field":k,"reason":"missing"}}}),400
    with SessionLocal() as db:
        user_id = data.get("user_id")
        if not user_id and data.get("user"):
            user = User(name=data["user"]["name"], email=data["user"].get("email"), tel=data["user"].get("tel"))
            db.add(user); db.commit(); db.refresh(user); user_id = user.user_id
        if not user_id:
            return jsonify({"error":{"code":"VALIDATION_ERROR","message":"user_id or user object is required","details":{"field":"user_id","reason":"missing"}}}),400

        plan = db.get(Plan, data["plan_id"])
        if not plan:
            return jsonify({"error":{"code":"NOT_FOUND","message":"plan not found","details":{"plan_id":data['plan_id']}}}),404

        start_dt = _parse_iso(data["start_datetime"])
        end_dt   = _parse_iso(data["end_datetime"])
        if end_dt <= start_dt:
            return jsonify({"error":{"code":"UNPROCESSABLE_ENTITY","message":"end_datetime must be later than start_datetime",
                                     "details":{"start_datetime":start_dt.isoformat(),"end_datetime":end_dt.isoformat()}}}),422

        if _overlaps(db, plan.plan_id, start_dt, end_dt):
            return jsonify({"error":{"code":"RESERVATION_OVERLAP","message":"time range overlaps existing reservation",
                                     "details":{"plan_id":plan.plan_id,"start_datetime":start_dt.isoformat(),"end_datetime":end_dt.isoformat()}}}),409

        r = Reservation(user_id=user_id, plan_id=plan.plan_id, start_datetime=start_dt, end_datetime=end_dt, note=data.get("note"))
        db.add(r); db.commit(); db.refresh(r)
        return jsonify({"reservation_id":r.reservation_id,"message":"created"}),201

@app.get("/api/reservations")
def list_reservations():
    date_str = request.args.get("date")
    start_q = request.args.get("start")
    end_q   = request.args.get("end")
    user_id = request.args.get("user_id", type=int)
    plan_id = request.args.get("plan_id", type=int)
    spot_id = request.args.get("booking_spot_id", type=int)

    with SessionLocal() as db:
        q = select(Reservation).order_by(Reservation.start_datetime.asc())
        if date_str:
            d = datetime.fromisoformat(date_str)
            day_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz.UTC)
            day_end = day_start + timedelta(days=1)
            q = q.where(and_(Reservation.start_datetime < day_end, Reservation.end_datetime > day_start))
        elif start_q and end_q:
            s = _parse_iso(start_q); e = _parse_iso(end_q)
            q = q.where(and_(Reservation.start_datetime < e, Reservation.end_datetime > s))
        if user_id:
            q = q.where(Reservation.user_id == user_id)
        if plan_id:
            q = q.where(Reservation.plan_id == plan_id)
        if spot_id:
            q = q.join(Reservation.plan).where(Plan.booking_spot_id == spot_id)

        rows = db.execute(q).scalars().all()
        def row(r: Reservation):
            return {
                "reservation_id": r.reservation_id,
                "user": {"user_id": r.user.user_id, "name": r.user.name} if r.user else None,
                "plan": {"plan_id": r.plan.plan_id, "name": r.plan.name, "booking_spot_id": r.plan.booking_spot_id} if r.plan else None,
                "start_datetime": r.start_datetime.replace(tzinfo=tz.UTC).isoformat(),
                "end_datetime": r.end_datetime.replace(tzinfo=tz.UTC).isoformat(),
                "note": r.note
            }
        data = [row(r) for r in rows]
        return jsonify({"data": data, "page": 1, "per_page": len(data), "total": len(data)})

@app.get("/api/reservations/<int:res_id>")
def get_reservation(res_id:int):
    with SessionLocal() as db:
        r = db.get(Reservation, res_id)
        if not r:
            return jsonify({"error":{"code":"NOT_FOUND","message":"reservation not found","details":{"reservation_id":res_id}}}),404
        return jsonify({
            "reservation_id": r.reservation_id,
            "user": {"user_id": r.user.user_id, "name": r.user.name, "email": r.user.email} if r.user else None,
            "plan": {"plan_id": r.plan.plan_id, "name": r.plan.name, "booking_spot_id": r.plan.booking_spot_id} if r.plan else None,
            "start_datetime": r.start_datetime.replace(tzinfo=tz.UTC).isoformat(),
            "end_datetime": r.end_datetime.replace(tzinfo=tz.UTC).isoformat(),
            "note": r.note,
            "created_at": r.created_at.replace(tzinfo=tz.UTC).isoformat()
        })

@app.patch("/api/reservations/<int:res_id>")
def update_reservation(res_id:int):
    data = request.get_json(force=True) or {}
    with SessionLocal() as db:
        r = db.get(Reservation, res_id)
        if not r:
            return jsonify({"error":{"code":"NOT_FOUND","message":"reservation not found","details":{"reservation_id":res_id}}}),404

        start_dt = r.start_datetime
        end_dt = r.end_datetime
        if "start_datetime" in data:
            start_dt = _parse_iso(data["start_datetime"])
        if "end_datetime" in data:
            end_dt = _parse_iso(data["end_datetime"])
        if end_dt <= start_dt:
            return jsonify({"error":{"code":"UNPROCESSABLE_ENTITY","message":"end_datetime must be later than start_datetime"}}),422

        new_plan_id = data.get("plan_id", r.plan_id)
        if _overlaps(db, new_plan_id, start_dt, end_dt, exclude_id=res_id):
            return jsonify({"error":{"code":"RESERVATION_OVERLAP","message":"time range overlaps existing reservation"}}),409

        if "user_id" in data: r.user_id = data["user_id"]
        if "plan_id" in data: r.plan_id = new_plan_id
        if "note" in data:    r.note = data["note"]
        r.start_datetime, r.end_datetime = start_dt, end_dt
        db.commit()
        return jsonify({"message":"updated"})

@app.delete("/api/reservations/<int:res_id>")
def delete_reservation(res_id:int):
    with SessionLocal() as db:
        r = db.get(Reservation, res_id)
        if not r:
            return jsonify({"error":{"code":"NOT_FOUND","message":"reservation not found","details":{"reservation_id":res_id}}}),404
        db.delete(r); db.commit()
        return jsonify({"message":"deleted"})
