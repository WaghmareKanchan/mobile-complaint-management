from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    batch_id = Column(String(12), index=True)
    customer_name = Column(String(80), nullable=False)
    phone = Column(String(20), nullable=False)
    model = Column(String(60))
    imei = Column(String(20), index=True, nullable=False)
    serial = Column(String(40))
    issue = Column(Text, nullable=False)
    status = Column(String(30), default="REGISTERED", index=True)
    error_code = Column(String(4))
    warranty_status = Column(String(20))
    issue_code = Column(String(30))
    priority = Column(String(10))
    sla_due = Column(DateTime)
    fast_track = Column(Boolean, default=False)
    quote_amount = Column(Integer)
    tracking_no = Column(String(40))
    new_imei = Column(String(15))
    delivered_at = Column(DateTime)
    pickup_type = Column(String(10))
    job_card_no = Column(String(20))
    condition_notes = Column(String(255))
    old_phone_collected = Column(Boolean, default=False)
    handover_otp = Column(String(6))
    feedback_rating = Column(Integer)
    feedback_text = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    history = relationship("History", order_by="History.id", cascade="all, delete-orphan")
    files = relationship("ComplaintFile", order_by="ComplaintFile.id")
class History(Base):
    __tablename__ = "complaint_history"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), index=True)
    status = Column(String(30))
    note = Column(String(255))
    at = Column(DateTime, default=datetime.utcnow)


class ComplaintFile(Base):
    __tablename__ = "complaint_files"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), index=True)
    kind = Column(String(10))
    stage = Column(String(30))
    original_name = Column(String(255))
    stored_name = Column(String(60))
    content_type = Column(String(40))
    size = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)