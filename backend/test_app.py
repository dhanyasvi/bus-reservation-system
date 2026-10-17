import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from main import app
from database import SessionLocal
import services as s
import config

client = TestClient(app)

def test_health_llm_resilient():
    """Health check should return 200 even with exhausted or missing API key credits."""
    resp = client.get("/health/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data

def test_seats_available():
    """Available seats endpoint should return valid seat information."""
    resp = client.get("/seats/available")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_seats" in data
    assert data["total_seats"] == 40
    assert "available_seats" in data
    assert isinstance(data["available_seats"], list)

def test_schedules_and_inventory():
    """Bus schedule and inventory retrieval."""
    resp = client.get("/schedules")
    assert resp.status_code == 200
    scheds = resp.json()
    assert isinstance(scheds, list)
    assert len(scheds) > 0
    s1 = scheds[0]
    assert "bus_number" in s1
    assert "fare" in s1
    assert "departure_time" in s1

def test_auth_and_access_control():
    """Passenger and admin authentication."""
    # 1. Passenger Login
    login_resp = client.post("/auth/login", json={"username": "RaviPassenger"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token

    # 2. Authenticated user profile
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["name"] == "RaviPassenger"

    # 3. Admin Login
    admin_login = client.post("/auth/admin-login", json={"admin_key": config.ADMIN_API_KEY})
    assert admin_login.status_code == 200
    assert admin_login.json()["role"] == "ADMIN"

def test_multi_agent_chat():
    """Multi-Agent conversation and specialized routing."""
    # Schedule inquiry routed to FleetScheduleAgent
    resp1 = client.post("/chat", json={
        "message": "What is the bus schedule from Bangalore to Chennai?",
        "history": [],
        "mode": "multi"
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "reply" in data1
    assert "agent" in data1
    assert "Specialist" in data1["agent"]

    # Booking inquiry routed to ReservationAgent
    resp2 = client.post("/chat", json={
        "message": "Book seat 33 from Bangalore to Chennai for Priya",
        "history": [],
        "mode": "multi"
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "reply" in data2
    assert "agent" in data2

def test_booking_crud_payment_and_refund():
    """Full lifecycle: Booking creation, payment verification, and 90% cancellation refund."""
    # 1. Direct booking with payment simulation
    book_resp = client.post("/bookings", json={
        "passenger_name": "RefundTester",
        "source": "Bangalore",
        "destination": "Chennai",
        "seat_no": 35
    })
    assert book_resp.status_code == 201
    booking = book_resp.json()
    b_id = booking["id"]
    assert booking["payment_status"] == "PAID"
    assert booking["transaction_id"].startswith("TXN_")
    assert booking["fare_amount"] > 0

    # 2. Check payment endpoint
    pay_resp = client.post(f"/bookings/{b_id}/payment", json={})
    assert pay_resp.status_code == 200
    assert pay_resp.json()["payment_status"] == "PAID"

    # 3. Cancel and verify 90% refund
    cancel_resp = client.delete(f"/bookings/{b_id}")
    assert cancel_resp.status_code == 200
    cancelled_b = cancel_resp.json()
    assert cancelled_b["status"] == "CANCELLED"
    assert cancelled_b["payment_status"] == "REFUNDED"
    assert cancelled_b["refund_amount"] == round(booking["fare_amount"] * 0.90, 2)

    # 4. Check refund status endpoint
    ref_resp = client.get(f"/bookings/{b_id}/refund")
    assert ref_resp.status_code == 200
    assert ref_resp.json()["refund_amount"] == cancelled_b["refund_amount"]
