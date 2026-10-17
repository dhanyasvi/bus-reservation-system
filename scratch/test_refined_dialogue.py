import sys
sys.path.insert(0, '.')
import re
from single_agent import CITY_ALIASES, _resolve_city, _extract_cities_from_text

def test_extraction():
    test_cases = [
        ("Bangalore to Chennai", ("Bangalore", "Chennai")),
        ("to Chennai from Bangalore", ("Bangalore", "Chennai")),
        ("Chennai from Bangalore", ("Bangalore", "Chennai")),
        ("from Bangalore to Chennai", ("Bangalore", "Chennai")),
        ("to Goa", (None, "Goa")),
        ("from Mumbai", ("Mumbai", None)),
        ("Goa", (None, "Goa")),
    ]
    for text, expected in test_cases:
        res = _extract_cities_from_text(text)
        print(f"'{text}' -> {res} (expected {expected})")
        assert res == expected, f"Failed for {text}: got {res}, expected {expected}"
    print("All extraction tests passed!")

if __name__ == "__main__":
    test_extraction()
