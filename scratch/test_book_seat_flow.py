import sys
sys.path.insert(0, '.')
from multi_agent import run_multi_agent
from tools import run_tool

def safe_print(*args):
    print(*(str(a).encode('ascii', errors='replace').decode('ascii') for a in args))

def test_book_seat_phrases():
    # Turn 1: User specifies route
    h1 = []
    t1 = "Bangalore to Chennai"
    r1 = run_multi_agent(t1, h1)
    safe_print("T1:", r1["reply"])
    assert "Bangalore" in r1["reply"] and "Chennai" in r1["reply"]

    # History after Turn 1
    h2 = [
        {"role": "user", "content": t1},
        {"role": "assistant", "content": r1["reply"]}
    ]

    # Find free seats
    seats_info = run_tool("get_available_seats", {})
    avail = seats_info.get("available_seats", [])
    s1 = avail[0]
    s2 = avail[1]
    s3 = avail[2]

    # Test case A: "book seat <s1> for Devi"
    r2a = run_multi_agent(f"book seat {s1} for Devi", h2)
    safe_print(f"\nT2A ('book seat {s1} for Devi'):", r2a["reply"])
    assert "Confirmed" in r2a["reply"], f"Expected Confirmed, got: {r2a['reply']}"

    # Test case B: "seat <s2> for Devi"
    r2b = run_multi_agent(f"seat {s2} for Devi", h2)
    safe_print(f"\nT2B ('seat {s2} for Devi'):", r2b["reply"])
    assert "Confirmed" in r2b["reply"], f"Expected Confirmed, got: {r2b['reply']}"

    # Test case C: "book seat <s3>"
    r2c = run_multi_agent(f"book seat {s3}", h2)
    safe_print(f"\nT2C ('book seat {s3}'):", r2c["reply"])
    assert "passenger" in r2c["reply"].lower() or "name" in r2c["reply"].lower(), f"Expected name prompt, got: {r2c['reply']}"

    # Follow up to C: "Devi"
    h3c = h2 + [
        {"role": "user", "content": f"book seat {s3}"},
        {"role": "assistant", "content": r2c["reply"]}
    ]
    r3c = run_multi_agent("Devi", h3c)
    safe_print("\nT3C ('Devi'):", r3c["reply"])
    assert "Confirmed" in r3c["reply"], f"Expected Confirmed, got: {r3c['reply']}"

    # Test case D: "book seat" -> should ask for seat or show available seats, NOT ask "where are you traveling from and to"
    r2d = run_multi_agent("book seat", h2)
    safe_print("\nT2D ('book seat'):", r2d["reply"])
    assert "from and to" not in r2d["reply"].lower(), f"Should not re-ask route! Got: {r2d['reply']}"
    assert "seat" in r2d["reply"].lower()

    safe_print("\nALL BOOK SEAT TESTS PASSED!")

if __name__ == "__main__":
    test_book_seat_phrases()
