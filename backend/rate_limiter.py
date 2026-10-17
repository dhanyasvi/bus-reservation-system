"""In-memory sliding window rate limiter for protecting endpoints against abuse."""
import time
from collections import defaultdict
from fastapi import Request, HTTPException

# Stores timestamps of requests per IP: { "127.0.0.1": [t1, t2, ...] }
_request_history = defaultdict(list)

def check_rate_limit(request: Request, max_requests: int = 60, window_seconds: int = 60):
    """
    Check if the client IP has exceeded the max allowed requests within the time window.
    Raises HTTPException(429) if limit exceeded.
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - window_seconds
    
    # Prune old timestamps
    timestamps = [t for t in _request_history[client_ip] if t > cutoff]
    
    if len(timestamps) >= max_requests:
        retry_after = int(window_seconds - (now - timestamps[0]))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per minute.",
            headers={"Retry-After": str(max(1, retry_after))}
        )
    
    timestamps.append(now)
    _request_history[client_ip] = timestamps
