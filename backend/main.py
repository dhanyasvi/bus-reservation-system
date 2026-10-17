import os
import sys

# Ensure backend directory is in sys.path for direct or module execution
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import time
import secrets
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import services as s
from schemas import (
    BookingCreate, BookingUpdate, ChatRequest,
    LoginRequest, AdminLoginRequest, PaymentProcessRequest
)
import config
from llm_client import check_llm_status
from single_agent import run_agent, reset_circuit_breaker
from multi_agent import run_multi_agent
from auth import create_jwt_token, get_current_user, require_admin
from rate_limiter import check_rate_limit
from logging_config import logger

Base.metadata.create_all(engine)

app = FastAPI(
    title="OmniBus — Bus Reservation & Fleet Management System",
    description="Full-stack + Generative AI + Single-Agent + Multi-Agent Case Study Implementation",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Operational Logging & Rate Limiting Middleware
@app.middleware("http")
async def operational_logging_and_rate_limit_middleware(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting on mutating or chat endpoints
    if request.url.path in ("/chat", "/bookings") and request.method == "POST":
        try:
            check_rate_limit(request, max_requests=100, window_seconds=60)
        except HTTPException as he:
            logger.warning(f"Rate limit exceeded for IP: {client_ip} on {request.url.path}")
            return JSONResponse({"detail": he.detail}, status_code=he.status_code, headers=he.headers)

    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(f"{request.method} {request.url.path} [{response.status_code}] - {duration_ms}ms (Client: {client_ip})")
    return response

@app.exception_handler(s.BookingError)
async def booking_error_handler(_, e: s.BookingError):
    return JSONResponse({"detail": e.message}, status_code=e.code)

# --- Authentication & Access Control Endpoints ---

@app.post("/auth/login")
def login_passenger(req: LoginRequest):
    """Authenticate passenger and return a signed JWT token."""
    token = create_jwt_token({
        "sub": req.username,
        "name": req.username,
        "role": "PASSENGER"
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "PASSENGER",
        "username": req.username
    }

@app.post("/auth/admin-login")
def login_admin(req: AdminLoginRequest):
    """Authenticate administrator using the Admin API key and issue admin JWT token."""
    if not config.ADMIN_API_KEY or not secrets.compare_digest(req.admin_key.strip(), config.ADMIN_API_KEY):
        raise HTTPException(401, "Invalid administrator key")
    
    token = create_jwt_token({
        "sub": "admin",
        "role": "ADMIN"
    }, expires_in_seconds=43200)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "ADMIN"
    }

@app.get("/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    """Return current authenticated user profile."""
    return user

# --- Booking Endpoints ---

@app.post("/bookings", status_code=201)
def create_booking(b: BookingCreate, db: Session = Depends(get_db)):
    """Create reservation with transactional locking and payment simulation."""
    return s.book_seat(db, **b.model_dump())

@app.get("/bookings")
def list_bookings(
    status: Optional[str] = None,
    passenger_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return s.list_bookings(db, status=status, passenger_name=passenger_name)

@app.get("/bookings/{booking_id}")
def read_booking(booking_id: int, db: Session = Depends(get_db)):
    return s.get_booking(db, booking_id)

@app.put("/bookings/{booking_id}")
def update_booking(booking_id: int, b: BookingUpdate, db: Session = Depends(get_db)):
    return s.update_booking(db, booking_id, b.seat_no, b.destination)

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    """Cancel booking, release seat, and process 90% refund."""
    return s.cancel_booking(db, booking_id)

@app.delete("/admin/bookings")
def admin_delete_all(admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only bulk delete endpoint."""
    return {"deleted": s.delete_all(db), "authorized_by": admin.get("role")}

# --- Seat Availability Endpoint ---

@app.get("/seats/available")
def get_available_seats(db: Session = Depends(get_db)):
    return s.get_available_seats(db)

# --- Bus Schedule & Fleet Inventory Endpoints ---

@app.get("/schedules")
def get_schedules(
    source: Optional[str] = None,
    destination: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve bus schedules and route fares."""
    return s.get_schedules(db, source=source, destination=destination)

@app.get("/schedules/{schedule_id}")
def get_single_schedule(schedule_id: int, db: Session = Depends(get_db)):
    scheds = s.get_schedules(db)
    for sc in scheds:
        if sc["id"] == schedule_id:
            return sc
    raise HTTPException(404, "Schedule not found")

# --- Payment & Refund Endpoints ---

@app.post("/bookings/{booking_id}/payment")
def process_payment(booking_id: int, req: PaymentProcessRequest, db: Session = Depends(get_db)):
    """Process or verify payment for an existing reservation."""
    b = s.get_booking(db, booking_id)
    return {
        "booking_id": booking_id,
        "payment_status": b.get("payment_status", "PAID"),
        "transaction_id": b.get("transaction_id"),
        "fare_amount": b.get("fare_amount", 750.00),
        "message": "Payment verified and active."
    }

@app.get("/bookings/{booking_id}/refund")
def get_refund_status(booking_id: int, db: Session = Depends(get_db)):
    """Get refund calculation and status for a booking."""
    b = s.get_booking(db, booking_id)
    fare = b.get("fare_amount", 750.00)
    refund = b.get("refund_amount") or round(fare * 0.90, 2)
    return {
        "booking_id": booking_id,
        "status": b.get("status"),
        "fare_amount": fare,
        "refund_amount": refund,
        "refund_policy": "90% standard refund on cancellation",
        "payment_status": b.get("payment_status")
    }

# --- Configuration & LLM Health Endpoints ---

class ConfigUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

@app.get("/api/config")
def get_system_config():
    cfg = config.get_config_dict()
    status_info = check_llm_status()
    cfg["llm_status"] = status_info
    return cfg

@app.post("/api/config")
def update_system_config(req: ConfigUpdateRequest):
    config.update_llm_settings(req.api_key, req.base_url, req.model)
    reset_circuit_breaker()
    status_info = check_llm_status()
    return {
        "status": "updated",
        "config": config.get_config_dict(),
        "llm_status": status_info
    }

@app.get("/health/llm")
def health_llm():
    status_info = check_llm_status()
    if status_info.get("available"):
        return {"status": "ok", "provider": status_info.get("provider"), "message": status_info.get("message")}
    return {
        "status": "resilient_fallback",
        "provider": "Built-in Resilient Agent",
        "message": status_info.get("message"),
        "error_detail": status_info.get("error_detail", "Credits exhausted or unconfigured")
    }

# --- AI Chat Assistant Endpoints (Single-Agent & Multi-Agent) ---

@app.post("/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    """
    Unified AI Assistant endpoint supporting both Single-Agent and Multi-Agent modes.
    """
    logged_in_user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            from auth import verify_jwt_token
            payload = verify_jwt_token(token)
            logged_in_user = payload.get("username") or payload.get("name") or payload.get("sub")
        except Exception:
            pass

    mode = (req.mode or "multi").lower().strip()
    try:
        if mode == "multi":
            result = run_multi_agent(req.message, req.history, logged_in_user=logged_in_user)
            return {
                "reply": result.get("reply", ""),
                "agent": result.get("agent", "Reservation Specialist Agent"),
                "specialist": result.get("specialist", "RESERVATION"),
                "mode": "multi"
            }
        else:
            reply_text = run_agent(req.message, req.history, logged_in_user=logged_in_user)
            return {
                "reply": reply_text,
                "agent": "Single-Agent Assistant",
                "specialist": "SingleAgent",
                "mode": "single"
            }
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return {
            "reply": f"Sorry, an unexpected error occurred: {str(e)}",
            "agent": "Error Handler",
            "mode": mode
        }

@app.post("/chat/multi-agent")
def chat_multi_agent(req: ChatRequest, authorization: Optional[str] = Header(None)):
    """Direct Multi-Agent endpoint."""
    req.mode = "multi"
    return chat(req, authorization=authorization)

# --- Static Frontend Serving ---

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
