from sqlalchemy import Column, Integer, String, Date, Boolean
from app.database import Base

class Device(Base):
    """Manufacturing DB record."""
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    imei = Column(String(15), unique=True, index=True, nullable=False)
    serial = Column(String(40), nullable=False)
    model = Column(String(60), nullable=False)
    sale_date = Column(Date)
    warranty_months = Column(Integer, default=12)
    blacklisted = Column(Boolean, default=False)
