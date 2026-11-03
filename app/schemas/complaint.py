from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

class DeviceIn(BaseModel):
    imei: str; serial: str; model: str; sale_date: date
    warranty_months: int = 12; blacklisted: bool = False

class ComplaintIn(BaseModel):
    customer_name: str; phone: str; model: Optional[str] = None
    imei: str; serial: Optional[str] = None; issue: str
    dead_on_arrival: bool = False; customer_caused: bool = False

class GuidanceIn(BaseModel): solved: bool

class TriageIn(BaseModel):
    issue_code: str
    priority: Literal["Critical", "High", "Medium", "Low"]

class ReceiveIn(BaseModel):
    customer_damage: bool = False
    condition_notes: Optional[str] = None

class DiagnoseIn(BaseModel): repairable: bool
class QuoteIn(BaseModel): amount: int
class DecisionIn(BaseModel): approved: bool
class RepairIn(BaseModel): qc_passed: bool

class ReplacementIn(BaseModel):
    new_imei: str
    new_serial: str
    collect_old: bool = True

class DispatchIn(BaseModel): tracking_no: str

class HandoverIn(BaseModel):
    otp: str

class FeedbackIn(BaseModel):
    satisfied: bool
    rating: Optional[int] = None
    comment: Optional[str] = None

class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str; note: Optional[str]; at: datetime

class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; kind: str; stage: Optional[str]; original_name: str; size: int; uploaded_at: datetime
class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; batch_id: Optional[str]; customer_name: str; phone: str
    model: Optional[str]; imei: str; serial: Optional[str]; issue: str
    status: str; error_code: Optional[str]; warranty_status: Optional[str]
    issue_code: Optional[str]; priority: Optional[str]; sla_due: Optional[datetime]
    fast_track: bool; quote_amount: Optional[int]; tracking_no: Optional[str]
    new_imei: Optional[str]; created_at: datetime
    pickup_type: Optional[str] = None; job_card_no: Optional[str] = None
    condition_notes: Optional[str] = None; old_phone_collected: Optional[bool] = None
    feedback_rating: Optional[int] = None; feedback_text: Optional[str] = None
    handover_otp: Optional[str] = None
    history: list[HistoryOut] = []
    files: list[FileOut] = []