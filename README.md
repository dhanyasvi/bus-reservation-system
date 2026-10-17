# Bus Reservation System (starter)
1. `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
2. `pip install -r requirements.txt`
3. Run `schema.sql` in MySQL; copy `.env.example` to `.env` and fill in values
4. `cd backend && uvicorn main:app --reload`
5. Open http://127.0.0.1:8000/docs
6. Check your key: GET /health/llm  -> {"status":"ok"}
7. Try POST /chat: {"message":"Book seat 5 from Bangalore to Chennai for Ravi"}
8. Admin: DELETE /admin/bookings with header `X-Admin-Key: <ADMIN_API_KEY>`
