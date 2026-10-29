import os
from sqlalchemy.engine import URL

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Kanchan@1234")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "complaint_db")

DATABASE_URL = os.getenv("DATABASE_URL") or URL.create(
    "mysql+pymysql", username=DB_USER, password=DB_PASSWORD,
    host=DB_HOST, port=DB_PORT, database=DB_NAME,
)

SLA_HOURS = {"Critical": 24, "High": 48, "Medium": 96, "Low": 168}