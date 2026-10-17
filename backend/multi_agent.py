"""
Multi-Agent Orchestration Architecture for OmniBus.
Implements a Supervisor/Orchestrator pattern directing specialized collaborative agents:
1. SupervisorAgent (Orchestrator & Intent Router)
2. ReservationAgent (Booking & Seat Allocation Specialist)
3. TicketManagementAgent (Modification, Cancellation Safeguard & Refund Specialist)
4. FleetScheduleAgent (Bus Schedules, Timings, & Inventory Specialist)
5. SupportAgent (Policy, Routes, & General Help Specialist)
"""

import re
import json
from typing import Optional
import openai
import config
from llm_client import get_client
from tools import TOOLS, run_tool
import single_agent as sa

# Multi-Agent Personas & System Prompts
SUPERVISOR_SYSTEM = """You are the Multi-Agent Supervisor for OmniBus Reservation System.
Your job is to route user requests to the appropriate specialist agent:
- RESERVATION: For booking new bus tickets, picking seats (1-40), passenger details, or ongoing reservation dialogues.
- MANAGEMENT: For modifying seat/destination, cancelling bookings, refund inquiries, or viewing ticket status.
- INVENTORY: For checking available seats, bus schedules, departure times, and fares.
- SUPPORT: For greetings, supported cities, general policies, or multi-question help.
Reply strictly with one token: RESERVATION, MANAGEMENT, INVENTORY, or SUPPORT."""

RESERVATION_SYSTEM = f"""You are the Reservation Specialist Agent for OmniBus.
Your role is to help passengers select valid routes, choose seats (1-40), verify passenger details, and confirm ticket bookings.

OmniBus Fleet Information:
- Supported Cities: {', '.join(sorted(list(config.CITIES)))}
- Total Seats per bus: 40 (numbered 1 to 40)
- Fare is automatically calculated based on the route schedule.

Available Tools:
- Use get_available_seats() to check which seats are vacant or when user asks for 'any seat'.
- Use book_seat(passenger_name, source, destination, seat_no) to book the reservation once details are confirmed.

Rules:
- CRITICAL: Never take or infer the departure/starting city from previous bookings or trips in chat history. Each booking must have departure and destination explicitly specified by the user.
- NEVER take a destination place as the starting place.
- Passenger name must be at least 2 characters.
- Departure and destination must be valid OmniBus cities and must differ.
- If any detail (source, destination, seat_no, passenger_name) is missing, ask the user specifically for it.
- When user asks for 'any seat' or 'auto seat', call get_available_seats and assign the first available seat.
- Report booking confirmation clearly with Booking ID, Passenger Name, Route, Seat Number, and Fare."""

MANAGEMENT_SYSTEM = """You are the Ticket Management & Cancellation Specialist Agent for OmniBus.
Your role is to look up bookings, modify reservations, and handle cancellations safely.

Available Tools:
- Use get_booking(booking_id) to retrieve booking details.
- Use list_bookings(passenger_name) to look up reservations by passenger name.
- Use update_booking(booking_id, seat_no, destination) to modify seat or destination.
- Use cancel_booking(booking_id) to cancel a reservation.

Rules:
- NEVER cancel a booking without asking the user to confirm first (e.g. 'Are you sure you want to cancel Booking #X?').
- If user confirms, call cancel_booking and report the 90% refund issued.
- You cannot delete all bookings; refuse bulk deletion requests politely.
- Report booking status and modifications clearly."""

INVENTORY_SYSTEM = f"""You are the Fleet & Schedule Specialist Agent for OmniBus.
Your role is to provide accurate, real-time information on bus schedules, departure/arrival times, fares, and seat availability.

OmniBus Fleet Information:
- Supported Cities: {', '.join(sorted(list(config.CITIES)))}
- Total Seats: 40

Available Tools:
- Use get_available_seats() to check coach capacity, booked seats, and open seats.
- Use get_schedules(source, destination) to look up daily route schedules, departure/arrival times, and fares.

Rules:
- If user asks about schedules between two cities, call get_schedules.
- If user asks which seats are free, call get_available_seats.
- Be concise, helpful, and present schedules and fares clearly in markdown."""

SUPPORT_SYSTEM = f"""You are the Customer Support & Policies Agent for OmniBus.
Your role is to assist passengers with general inquiries, company policies, routes, and overall guidance.

OmniBus Policies & Fleet Info:
- Supported Cities: {', '.join(sorted(list(config.CITIES)))}
- Fleet: Premium 40-seat air-conditioned and executive sleeper buses.
- Cancellation Policy: Cancellations are permitted at any time prior to departure and receive an instant 90% refund.
- Bulk Deletions: Bulk booking deletions require administrator authorization.

Rules:
- Provide warm, professional, and courteous customer support.
- Direct passengers to the Reservation Specialist Agent for booking tickets."""

def _classify_intent_supervisor(user_message: str, history: list[dict]) -> str:
    """Classifies user intent to route to the appropriate specialist agent."""
    msg = user_message.lower().strip()

    # 1. Cancellations & modifications & lookups -> MANAGEMENT
    if any(k in msg for k in [
        "cancel", "change", "modify", "update", "my booking", "lookup", "reschedule",
        "refund", "ticket status", "booking status", "my ticket", "view booking"
    ]):
        return "MANAGEMENT"
    
    # Check if last assistant asked for cancellation confirmation or modification
    for h in reversed(history[-2:]):
        if h.get("role") == "assistant":
            c = h.get("content", "").lower()
            if "sure you want to cancel" in c or "confirm cancel" in c or "would you like to change" in c:
                return "MANAGEMENT"

    # 2. Schedules & available seats inquiry -> INVENTORY
    # (Only if not a direct booking request like "book seat 5")
    is_direct_booking = any(k in msg for k in ["book", "reserve"])
    if not is_direct_booking and any(k in msg for k in [
        "schedule", "timing", "timings", "departure", "arrival", "fare", "fares", "price", "prices",
        "how much", "available", "free seat", "seats left", "empty", "capacity", "how many seat"
    ]):
        return "INVENTORY"

    # 3. Ongoing booking dialogue -> RESERVATION
    # Check if last assistant asked a booking slot question
    for h in reversed(history[-2:]):
        if h.get("role") == "assistant":
            c = h.get("content", "").lower()
            if any(term in c for term in ["confirmed", "cancelled", "cancel"]):
                break
            if any(q in c for q in [
                "which seat number", "which seat", "available seats include",
                "passenger's full name", "passenger name", "who is the passenger",
                "departing from", "departure city", "travel to from", "where will you be departing",
                "where are you traveling from and to", "where would you like to travel"
            ]):
                return "RESERVATION"

    # 4. New booking intent -> RESERVATION
    if any(k in msg for k in [
        "book", "reserve", "ticket", "tickets", "seat", "seats", "travel", "journey", "trip",
        "going to", "want to go", "head to", "fly", "drive", "take a bus", "need a bus", "need a seat"
    ]):
        return "RESERVATION"

    # Check if user mentioned cities (e.g. "Bangalore to Chennai" or "to Goa") -> RESERVATION
    s, d = sa._extract_cities_from_text(user_message)
    if s or d:
        return "RESERVATION"

    # 5. Policies & routes overview -> SUPPORT
    if any(k in msg for k in ["cities", "routes", "destinations", "operate", "policy", "refund policy", "help", "support"]):
        return "SUPPORT"

    # Default -> SUPPORT / GENERAL
    return "SUPPORT"

def run_multi_agent(user_message: str, history: list[dict], logged_in_user: Optional[str] = None) -> dict:
    """
    Executes the Multi-Agent team workflow:
    1. Supervisor classifies intent and selects Specialist Agent.
    2. Selected Specialist executes tools or applies specialized rules.
    3. Returns response annotated with specialist attribution.
    """
    specialist_type = _classify_intent_supervisor(user_message, history)
    agent_names = {
        "RESERVATION": "Reservation Specialist Agent",
        "MANAGEMENT": "Ticket Management Specialist Agent",
        "INVENTORY": "Fleet & Schedule Specialist Agent",
        "SUPPORT": "Customer Support & Policies Agent"
    }
    agent_name = agent_names.get(specialist_type, "Reservation Specialist Agent")

    # If LLM key is available and circuit is closed, run LLM with specialized agent prompt
    if config.LLM_API_KEY and config.LLM_API_KEY.strip() and not sa.is_circuit_open():
        try:
            client = get_client()
            prompts = {
                "RESERVATION": RESERVATION_SYSTEM,
                "MANAGEMENT": MANAGEMENT_SYSTEM,
                "INVENTORY": INVENTORY_SYSTEM,
                "SUPPORT": SUPPORT_SYSTEM
            }
            system_prompt = prompts.get(specialist_type, RESERVATION_SYSTEM)
            msgs = [{"role": "system", "content": system_prompt}]
            
            # Filter history to prevent taking past history during booking in chat
            filtered = [m for m in history if m.get("role") in ("user", "assistant")]
            if specialist_type == "RESERVATION":
                # Only reset history if a previous booking was confirmed or user provides a whole new route
                s_msg, d_msg = sa._extract_cities_from_text(user_message)
                clean_hist = []
                for h in reversed(filtered[-4:]):
                    c = h.get("content", "").lower()
                    if any(term in c for term in ["confirmed", "has been cancelled", "cancelled successfully", "already cancelled"]):
                        break
                    clean_hist.insert(0, h)
                if s_msg and d_msg:
                    clean_hist = []
                active_history = clean_hist
            else:
                active_history = filtered[-10:]

            if active_history and active_history[-1].get("role") == "user" and active_history[-1].get("content") == user_message:
                msgs += active_history
            else:
                msgs += active_history
                msgs.append({"role": "user", "content": user_message})

            for _ in range(5):
                resp = client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=msgs,
                    tools=TOOLS
                )
                m = resp.choices[0].message
                if not m.tool_calls:
                    return {
                        "reply": m.content or "",
                        "agent": agent_name,
                        "specialist": specialist_type,
                        "mode": "multi_agent_llm"
                    }
                msgs.append(m)
                for tc in m.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = run_tool(tc.function.name, args)
                    msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
            
            return {
                "reply": "Could not complete operation in agent rounds.",
                "agent": agent_name,
                "specialist": specialist_type,
                "mode": "multi_agent_llm"
            }
        except (openai.RateLimitError, openai.AuthenticationError):
            sa.trip_circuit_breaker(600)
        except Exception:
            pass

    # Resilient Multi-Agent Execution:
    # Dedicated schedule specialist handling for schedule queries
    if specialist_type == "INVENTORY" and any(k in user_message.lower() for k in ["schedule", "timing", "timings", "departure", "fare", "bus number"]):
        src, dst = sa._extract_cities_from_text(user_message)
        schedules = run_tool("get_schedules", {"source": src, "destination": dst} if (src or dst) else {})
        if isinstance(schedules, list) and schedules:
            lines = [f"🚌 **OmniBus Route Schedules ({len(schedules)} daily service{'s' if len(schedules) > 1 else ''})**:"]
            for s in schedules[:6]:
                lines.append(f"• **{s['bus_number']}** ({s['bus_type']}): {s['source']} ({s['departure_time']}) ➔ {s['destination']} ({s['arrival_time']}) | **₹{s['fare']}**")
            lines.append("\nWould you like to book one of these buses? Simply tell me the passenger name and seat!")
            return {
                "reply": "\n".join(lines),
                "agent": agent_name,
                "specialist": specialist_type,
                "mode": "multi_agent_resilient"
            }

    # For Resilient Agent, also use clean active_history if RESERVATION
    resilient_history = active_history if 'active_history' in locals() else history
    reply, detected_intent = sa.run_resilient_agent_with_intent(user_message, resilient_history, logged_in_user=logged_in_user)
    final_specialist = detected_intent or specialist_type
    final_agent = agent_names.get(final_specialist, agent_name)

    return {
        "reply": reply,
        "agent": final_agent,
        "specialist": final_specialist,
        "mode": "multi_agent_resilient"
    }
