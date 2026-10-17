import sys
sys.path.insert(0, '.')
from single_agent import _accumulate_dialogue_state, run_resilient_agent_with_intent
from multi_agent import run_multi_agent

def run_tests():
    print("Testing booking flows without stale history pollution...")

    # Scenario 1: Previous booking was confirmed for Bangalore -> Chennai.
    # Now user says "to Goa" or "Book ticket to Goa" or "Chennai to Mumbai".
    # Previous destination (Chennai) must NEVER become the starting place!
    history_after_booking = [
        {"role": "user", "content": "Book seat 5 from Bangalore to Chennai for Ravi"},
        {"role": "assistant", "content": "🎉 **Booking Confirmed!**\n- **Booking ID**: #101\n- **Passenger**: Ravi\n- **Route**: Bangalore ➔ Chennai\n- **Seat**: 5\n- **Fare**: ₹750"}
    ]

    # Test 1a: "Book ticket to Goa"
    st = _accumulate_dialogue_state("Book ticket to Goa", history_after_booking)
    assert st["destination"] == "Goa", f"Expected destination Goa, got {st['destination']}"
    assert st["source"] is None, f"Expected source None, but got {st['source']} (it took history!)"

    # Test 1b: "to Goa"
    st = _accumulate_dialogue_state("to Goa", history_after_booking)
    assert st["destination"] == "Goa", f"Expected destination Goa, got {st['destination']}"
    assert st["source"] is None, f"Expected source None, but got {st['source']} (it took history!)"

    # Test 1c: "Chennai to Mumbai"
    st = _accumulate_dialogue_state("Chennai to Mumbai", history_after_booking)
    assert st["source"] == "Chennai", f"Expected source Chennai, got {st['source']}"
    assert st["destination"] == "Mumbai", f"Expected destination Mumbai, got {st['destination']}"

    # Scenario 2: User was asked "Where will you be departing from for your trip to Mumbai?"
    # and user replies "to Goa". It must NOT set source=Goa and destination=Mumbai!
    history_ask_source = [
        {"role": "user", "content": "Book ticket to Mumbai"},
        {"role": "assistant", "content": "Where will you be departing from for your trip to **Mumbai**? (e.g. *'From Bangalore'* or *'Pune'*)"}
    ]

    st = _accumulate_dialogue_state("to Goa", history_ask_source)
    assert st["destination"] == "Goa", f"Expected destination Goa, got {st['destination']}"
    assert st["source"] is None, f"Source should NOT be Goa or Mumbai! Got {st['source']}"

    # Scenario 3: User answers "Bangalore" or "From Bangalore" to "Where will you be departing from for your trip to Mumbai?"
    st = _accumulate_dialogue_state("Bangalore", history_ask_source)
    assert st["source"] == "Bangalore", f"Expected source Bangalore, got {st['source']}"
    assert st["destination"] == "Mumbai", f"Expected destination Mumbai, got {st['destination']}"

    # Scenario 4: User is asked "Traveling from Bangalore to Chennai! Which seat number (1-40) would you like? And who is the passenger?"
    # If user replies "Seat 5 for Devi" -> seat=5, name=Devi, route preserved.
    # But if user replies "to Goa" or "Mumbai to Pune" -> route MUST NOT be Bangalore -> Chennai!
    history_ask_seat = [
        {"role": "user", "content": "Bangalore to Chennai"},
        {"role": "assistant", "content": "Traveling from **Bangalore** to **Chennai**! Which seat number (1-40) would you like? And who is the passenger?"}
    ]

    st_reply = _accumulate_dialogue_state("Seat 5 for Devi", history_ask_seat)
    assert st_reply["source"] == "Bangalore" and st_reply["destination"] == "Chennai"
    assert st_reply["seat_no"] == 5 and st_reply["passenger_name"] == "Devi"

    st_override = _accumulate_dialogue_state("to Goa", history_ask_seat)
    assert st_override["destination"] == "Goa"
    assert st_override["source"] is None, f"Old source Bangalore must NOT be kept! Got {st_override['source']}"

    # Scenario 5: Multi-agent execution of the above scenarios
    resp = run_multi_agent("to Goa", history_after_booking)
    print("Multi-agent reply to 'to Goa' after confirmed booking:\n", resp["reply"])
    assert "trip to **Goa**" in resp["reply"] or "to **Goa**" in resp["reply"]
    assert "Chennai" not in resp["reply"]

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
