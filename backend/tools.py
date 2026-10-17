"""Tool schemas for the LLM. NOTE: delete_all is deliberately NOT here."""
import json
from database import SessionLocal
import services as s

TOOLS = [
    {"type": "function", "function": {
        "name": "book_seat", "description": "Book a seat between two cities.",
        "parameters": {"type": "object", "properties": {
            "passenger_name": {"type": "string"}, "source": {"type": "string"},
            "destination": {"type": "string"}, "seat_no": {"type": "integer"}},
            "required": ["passenger_name", "source", "destination", "seat_no"]}}},
    {"type": "function", "function": {
        "name": "get_booking", "description": "Look up a booking by id.",
        "parameters": {"type": "object", "properties": {"booking_id": {"type": "integer"}},
                       "required": ["booking_id"]}}},
    {"type": "function", "function": {
        "name": "update_booking", "description": "Change seat and/or destination of a booking.",
        "parameters": {"type": "object", "properties": {
            "booking_id": {"type": "integer"}, "seat_no": {"type": "integer"},
            "destination": {"type": "string"}}, "required": ["booking_id"]}}},
    {"type": "function", "function": {
        "name": "cancel_booking", "description": "Cancel a booking (only after user confirms).",
        "parameters": {"type": "object", "properties": {"booking_id": {"type": "integer"}},
                       "required": ["booking_id"]}}},
    {"type": "function", "function": {
        "name": "get_available_seats", "description": "Check bus seat availability and view all available and booked seats.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "list_bookings", "description": "List all bookings or search bookings by passenger name.",
        "parameters": {"type": "object", "properties": {
            "passenger_name": {"type": "string", "description": "Optional passenger name to search for"}
        }}}},
    {"type": "function", "function": {
        "name": "get_schedules", "description": "Look up bus schedules, departure/arrival timings, and fares between cities.",
        "parameters": {"type": "object", "properties": {
            "source": {"type": "string", "description": "Optional departure city"},
            "destination": {"type": "string", "description": "Optional destination city"}
        }}}}
]

_FUNCS = {
    "book_seat": s.book_seat,
    "get_booking": s.get_booking,
    "update_booking": s.update_booking,
    "cancel_booking": s.cancel_booking,
    "get_available_seats": s.get_available_seats,
    "list_bookings": s.list_bookings,
    "get_schedules": s.get_schedules
}

def run_tool(name: str, args: dict) -> dict:
    if name not in _FUNCS:
        return {"error": f"Unknown tool {name}"}
    db = SessionLocal()
    try:
        return _FUNCS[name](db, **args)
    except s.BookingError as e:
        db.rollback()
        return {"error": e.message}
    except TypeError as e:
        return {"error": f"Bad arguments: {e}"}
    finally:
        db.close()
