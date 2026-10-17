from typing import Optional
from pydantic import BaseModel, Field

class BookingCreate(BaseModel):
    passenger_name: str = Field(min_length=2, max_length=80)
    source: str
    destination: str
    seat_no: int = Field(ge=1, le=40)

class BookingUpdate(BaseModel):
    seat_no: Optional[int] = Field(default=None, ge=1, le=40)
    destination: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = []
    mode: Optional[str] = "multi"  # "single" or "multi"

class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: Optional[str] = "password"

class AdminLoginRequest(BaseModel):
    admin_key: str

class PaymentProcessRequest(BaseModel):
    amount: Optional[float] = None
    payment_method: Optional[str] = "UPI / Card"
