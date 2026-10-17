import secrets
from typing import Optional
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from models import Booking, Schedule
from config import CITIES, MAX_SEAT

class BookingError(Exception):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.message, self.code = message, code

def to_dict(b: Booking) -> dict:
    return {
        "id": b.id,
        "passenger_name": b.passenger_name,
        "source": b.source,
        "destination": b.destination,
        "seat_no": b.seat_no,
        "status": b.status,
        "fare_amount": float(b.fare_amount) if b.fare_amount is not None else 750.00,
        "payment_status": b.payment_status or "PAID",
        "refund_amount": float(b.refund_amount) if b.refund_amount is not None else None,
        "transaction_id": b.transaction_id or "",
        "user_id": b.user_id or (b.passenger_name.strip().lower().replace(" ", "_") if b.passenger_name else "guest")
    }

def check_booking_authorization(b: Booking, user: Optional[dict] = None) -> None:
    """
    Enforce that passengers can ONLY view, modify, pay for, or cancel their OWN bookings.
    Administrators (role='ADMIN') have full authority across all bookings.
    """
    if not user:
        return
    
    role = (user.get("role") or "").upper()
    if role == "ADMIN":
        return
    
    current_username = (user.get("username") or user.get("sub") or "").strip().lower()
    if not current_username or current_username == "guest":
        return

    booking_user = (b.user_id or "").strip().lower()
    passenger = (b.passenger_name or "").strip().lower()
    clean_current = current_username.replace(" ", "_")

    is_owner = (
        clean_current == booking_user or
        current_username == booking_user or
        current_username == passenger or
        clean_current == passenger.replace(" ", "_")
    )

    if not is_owner:
        owner_display = b.user_id or b.passenger_name
        raise BookingError(
            f"Access Denied: You cannot modify or access another passenger's reservation. This booking belongs to '{owner_display}'.",
            403
        )

def schedule_to_dict(s: Schedule) -> dict:
    return {
        "id": s.id,
        "bus_number": s.bus_number,
        "source": s.source,
        "destination": s.destination,
        "departure_time": s.departure_time,
        "arrival_time": s.arrival_time,
        "bus_type": s.bus_type,
        "fare": float(s.fare),
        "total_seats": s.total_seats
    }

def _city(name: str) -> str:
    c = (name or "").strip().title()
    if c not in CITIES:
        raise BookingError(f"Unknown city '{name}'. Valid: {', '.join(sorted(CITIES))}")
    return c

def _seat_free(db: Session, seat_no: int, ignore_id=None):
    """
    Check if a seat is valid and available.
    TRANSACTIONAL LOCKING: Uses pessimistic select ... for update (with_for_update)
    to lock the seat record and strictly prevent race conditions and double bookings.
    """
    if not isinstance(seat_no, int) or not 1 <= seat_no <= MAX_SEAT:
        raise BookingError(f"Seat must be between 1 and {MAX_SEAT}")
    q = select(Booking).where(Booking.seat_no == seat_no).with_for_update()
    taken = db.execute(q).scalar_one_or_none()
    if taken and taken.id != ignore_id:
        raise BookingError(f"Seat {seat_no} is already booked", 409)

def _get(db: Session, booking_id: int) -> Booking:
    b = db.get(Booking, booking_id)
    if not b:
        raise BookingError(f"Booking {booking_id} not found", 404)
    return b

def _get_route_fare(db: Session, source: str, destination: str) -> float:
    """Find schedule fare for route or provide default fare."""
    q = select(Schedule).where(Schedule.source == source, Schedule.destination == destination)
    sched = db.execute(q).scalars().first()
    if sched:
        return float(sched.fare)
    return 750.00

def book_seat(
    db: Session,
    passenger_name: str,
    source: str,
    destination: str,
    seat_no: int,
    user_id: Optional[str] = None
) -> dict:
    """Book a seat, perform transactional locking, simulate payment processing, and confirm reservation."""
    name = (passenger_name or "").strip()
    if len(name) < 2:
        raise BookingError("Passenger name must be at least 2 characters")
    src, dst = _city(source), _city(destination)
    if src == dst:
        raise BookingError("Source and destination must differ")
    
    # Transactional locking on seat
    _seat_free(db, seat_no)

    fare = _get_route_fare(db, src, dst)
    txn_id = f"TXN_{secrets.token_hex(4).upper()}"
    final_user_id = (user_id or name.lower().replace(" ", "_")).strip()

    b = Booking(
        passenger_name=name,
        source=src,
        destination=dst,
        seat_no=seat_no,
        status="CONFIRMED",
        fare_amount=fare,
        payment_status="PAID",
        transaction_id=txn_id,
        user_id=final_user_id
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return to_dict(b)

def get_booking(db: Session, booking_id: int, user: Optional[dict] = None) -> dict:
    b = _get(db, booking_id)
    if user:
        check_booking_authorization(b, user)
    return to_dict(b)

def update_booking(
    db: Session,
    booking_id: int,
    seat_no=None,
    destination=None,
    user: Optional[dict] = None
) -> dict:
    b = _get(db, booking_id)
    if user:
        check_booking_authorization(b, user)
    if b.status == "CANCELLED":
        raise BookingError("Cancelled bookings cannot be modified", 409)
    if seat_no is None and destination is None:
        raise BookingError("Provide a new seat_no and/or destination")
    if destination is not None:
        dst = _city(destination)
        if dst == b.source:
            raise BookingError("Source and destination must differ")
        b.destination = dst
        # Recalculate fare
        b.fare_amount = _get_route_fare(db, b.source, dst)
    if seat_no is not None:
        _seat_free(db, seat_no, ignore_id=b.id)
        b.seat_no = seat_no
    db.commit()
    db.refresh(b)
    return to_dict(b)

def cancel_booking(db: Session, booking_id: int, user: Optional[dict] = None) -> dict:
    """Cancel booking, free the seat, and process payment refund (90% standard refund policy)."""
    b = _get(db, booking_id)
    if user:
        check_booking_authorization(b, user)
    if b.status == "CANCELLED":
        raise BookingError("Already cancelled", 409)
    
    # Calculate 90% refund
    fare = float(b.fare_amount) if b.fare_amount else 750.00
    refund = round(fare * 0.90, 2)

    b.status = "CANCELLED"
    b.seat_no = None
    b.payment_status = "REFUNDED"
    b.refund_amount = refund
    
    db.commit()
    db.refresh(b)
    return to_dict(b)

def delete_all(db: Session) -> int:
    n = db.query(Booking).delete()
    db.commit()
    return n

def get_available_seats(db: Session) -> dict:
    """Return seat statistics and list of available / booked seats."""
    q = select(Booking).where(Booking.seat_no.is_not(None), Booking.status == "CONFIRMED")
    bookings = db.execute(q).scalars().all()
    booked_map = {
        b.seat_no: {
            "booking_id": b.id,
            "passenger_name": b.passenger_name,
            "source": b.source,
            "destination": b.destination
        }
        for b in bookings
    }
    booked_seats = sorted(list(booked_map.keys()))
    available_seats = [i for i in range(1, MAX_SEAT + 1) if i not in booked_map]
    return {
        "total_seats": MAX_SEAT,
        "available_count": len(available_seats),
        "booked_count": len(booked_seats),
        "available_seats": available_seats,
        "booked_seats": booked_seats,
        "booked_details": booked_map
    }

def list_bookings(
    db: Session,
    status: Optional[str] = None,
    passenger_name: Optional[str] = None,
    user_id: Optional[str] = None,
    user: Optional[dict] = None
) -> list[dict]:
    """
    List bookings strictly scoped to the logged-in user:
    - If user is ADMIN: can view all bookings across the fleet.
    - If user is PASSENGER: ONLY view bookings belonging to that passenger account.
    - If no user context provided: filters by user_id or passenger_name if present.
    """
    q = select(Booking)
    if status:
        q = q.where(Booking.status == status.upper().strip())

    if user and user.get("role") != "ADMIN":
        target_name = (user.get("username") or user.get("sub") or "").strip().lower()
        if target_name and target_name != "guest":
            target_clean = target_name.replace(" ", "_")
            q = q.where(
                or_(
                    func.lower(Booking.user_id) == target_clean,
                    func.lower(Booking.user_id) == target_name,
                    func.lower(Booking.passenger_name) == target_name,
                    func.lower(Booking.passenger_name) == target_clean
                )
            )
        else:
            q = q.where(func.lower(Booking.user_id) == "guest")
    elif user_id:
        u_clean = user_id.strip().lower().replace(" ", "_")
        q = q.where(
            or_(
                func.lower(Booking.user_id) == u_clean,
                func.lower(Booking.user_id) == user_id.strip().lower()
            )
        )
    elif passenger_name:
        q = q.where(Booking.passenger_name.ilike(f"%{passenger_name.strip()}%"))

    bookings = db.execute(q.order_by(Booking.id.desc())).scalars().all()
    return [to_dict(b) for b in bookings]

def get_schedules(db: Session, source: str = None, destination: str = None) -> list[dict]:
    """Retrieve bus route schedules and inventory."""
    q = select(Schedule)
    if source:
        q = q.where(Schedule.source.ilike(f"%{source.strip()}%"))
    if destination:
        q = q.where(Schedule.destination.ilike(f"%{destination.strip()}%"))
    schedules = db.execute(q.order_by(Schedule.id)).scalars().all()
    return [schedule_to_dict(s) for s in schedules]
