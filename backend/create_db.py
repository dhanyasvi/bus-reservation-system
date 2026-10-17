from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url, URL
from config import DB_URL

u = make_url(DB_URL)
server_url = URL.create(
    drivername=u.drivername,
    username=u.username,
    password=u.password,
    host=u.host,
    port=u.port,
)

engine = create_engine(server_url)
with engine.connect() as conn:
    conn.execute(text("CREATE DATABASE IF NOT EXISTS busdb"))
    conn.commit()

print("busdb created")