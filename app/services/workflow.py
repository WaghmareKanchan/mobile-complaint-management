import secrets
import re, secrets
from datetime import datetime, timedelta, date
from sqlalchemy import func
from app.models import Complaint, History, Device
from app.services.errors import FlowError
from app.services.verification import verify
from app.services.warranty import warranty_valid
from app.services.priority import sla_due, is_urgent
from app.services.imei import valid_imei

def move(db, c, status, note=""):
    c.status = status
    db.add(History(complaint_id=c.id, status=status, note=note[:255]))

def require(c, *allowed):
    if c.status not in allowed:
        raise FlowError(409, "E99", f"Action not allowed in status {c.status}")

def register(db, d, batch_id=None):
    d.phone = (d.phone or "").strip()
    if not re.fullmatch(r"\d{10}", d.phone):
        raise FlowError(422, "E13", "Phone number must be exactly 10 digits")
    code, dev, msg = verify(db, d.imei, d.serial)
    c = Complaint(customer_name=d.customer_name, phone=d.phone, imei=d.imei, serial=d.serial,
                  model=d.model or (dev.model if dev else None), issue=d.issue, batch_id=batch_id)
    db.add(c); db.flush()
    move(db, c, "REGISTERED", "Complaint created")
    if code:
        c.error_code = code
        move(db, c, "ON_HOLD", f"{code} {msg}")
        db.commit(); return c
    move(db, c, "VERIFIED", "IMEI verified")
    ok = warranty_valid(dev) and not d.customer_caused
    c.warranty_status = "IN_WARRANTY" if ok else "OUT_OF_WARRANTY"
    move(db, c, "VERIFIED", "In-warranty: free repair/replacement" if ok else "Out-of-warranty: chargeable (quote after diagnosis)")
    age = (date.today() - dev.sale_date).days if dev.sale_date else None
    doa = d.dead_on_arrival and age is not None and age <= 7
    same = db.query(Complaint).filter(Complaint.imei == d.imei, Complaint.id != c.id, Complaint.status == "CLOSED",
             func.lower(func.trim(Complaint.issue)) == d.issue.strip().lower()).count()
    if d.dead_on_arrival and not doa:
        move(db, c, "VERIFIED", f"Dead-on-arrival ignored: phone sold {age} days ago (limit 7)")
    if ok and (doa or same >= 2):
        c.fast_track = True
        move(db, c, "FAST_TRACK", "Dead on arrival (7 days) or same issue 3 times: fast-track replacement")
    else:
        move(db, c, "FIRST_LEVEL_HELP", "Dealer: restart, other charger, update, safe mode, backup+reset")
    db.commit(); return c

def guidance(db, c, solved):
    require(c, "FIRST_LEVEL_HELP")
    if solved: move(db, c, "CLOSED", "Resolved by guidance")
    else: move(db, c, "FIRST_LEVEL_HELP", "Not solved by guidance: triage next")
    db.commit(); return c

def triage(db, c, issue_code, priority):
    require(c, "FIRST_LEVEL_HELP")
    c.issue_code, c.priority, c.sla_due = issue_code, priority, sla_due(priority)
    base = "Issue code, priority and SLA due date saved."
    if is_urgent(priority):
        c.pickup_type = "URGENT"
        note = "STOP using, STOP charging, keep away from heat. Urgent pickup/courier within 24h. " + base
    else:
        c.pickup_type = "NORMAL"
        note = "Dealer acknowledged with expected date (SLA), normal pickup. " + base
    move(db, c, "TRIAGED", note)
    db.commit(); return c

def receive(db, c, customer_damage, condition_notes=None):
    require(c, "TRIAGED")
    c.job_card_no = f"JC-{c.id:06d}"
    c.condition_notes = condition_notes
    note = "Phone received at service centre, job card created."
    if customer_damage and c.warranty_status == "IN_WARRANTY":
        c.warranty_status = "OUT_OF_WARRANTY"
        note = "Customer damage found: re-classified OUT_OF_WARRANTY, customer informed. " + note
    move(db, c, "DIAGNOSING", note)
    db.commit(); return c

def diagnose(db, c, repairable):
    require(c, "DIAGNOSING", "REOPENED")
    inw = c.warranty_status == "IN_WARRANTY"
    if repairable:
        if inw: move(db, c, "REPAIRING", "Repairable, free")
        else: move(db, c, "QUOTE_PENDING", "Repairable, chargeable: send quote")
    elif inw:
        move(db, c, "REPLACEMENT_PENDING", "Not repairable: replacement allowed")
    else:
        move(db, c, "CLOSED", "Not repairable: return phone, close")
    db.commit(); return c

def send_quote(db, c, amount):
    require(c, "QUOTE_PENDING")
    c.quote_amount = amount
    move(db, c, "QUOTE_SENT", "Repair quote sent to customer")
    db.commit(); return c

def quote_decision(db, c, approved):
    require(c, "QUOTE_SENT")
    if approved: move(db, c, "REPAIRING", "Customer approved quote")
    else: move(db, c, "CLOSED", "Declined: return phone, close")
    db.commit(); return c

def finish_repair(db, c, qc_passed):
    require(c, "REPAIRING")
    if qc_passed: move(db, c, "QC_PASSED", "Final QC passed")
    else: move(db, c, "REPAIRING", "QC failed: repair again")
    db.commit(); return c

def approve_replacement(db, c, new_imei, new_serial, collect_old=True):
    require(c, "FAST_TRACK", "REPLACEMENT_PENDING")
    if not valid_imei(new_imei):
        raise FlowError(422, "E01", "New IMEI is invalid")
    if db.query(Device).filter_by(imei=new_imei).first():
        raise FlowError(409, "E08", "New IMEI is already in the Manufacturing DB")
    old = db.query(Device).filter_by(imei=c.imei).first()
    db.add(Device(imei=new_imei, serial=new_serial, model=(old.model if old else c.model) or "",
                  sale_date=date.today(), warranty_months=(old.warranty_months if old else 12)))
    c.new_imei, c.old_phone_collected = new_imei, collect_old
    move(db, c, "REPLACEMENT_APPROVED", "Replacement approved: new phone added to Manufacturing DB with new warranty")
    db.commit(); return c

def dispatch(db, c, tracking_no):
    require(c, "QC_PASSED", "REPLACEMENT_APPROVED")
    c.tracking_no, c.handover_otp = tracking_no, f"{secrets.randbelow(10000):04d}"
    move(db, c, "DISPATCHED", "Dispatched to dealer by courier")
    db.commit(); return c

def handover(db, c, otp):
    require(c, "DISPATCHED")
    if otp.strip() != c.handover_otp:
        raise FlowError(422, "E09", "Wrong OTP: ask the customer for the code sent to them")
    c.delivered_at = datetime.utcnow()
    move(db, c, "DELIVERED", "Customer checked phone, OTP verified")
    db.commit(); return c

def feedback(db, c, satisfied, rating=None, comment=None):
    require(c, "DELIVERED")
    if rating is not None and not 1 <= rating <= 5:
        raise FlowError(422, "E10", "Rating must be 1 to 5")
    c.feedback_rating, c.feedback_text = rating, comment
    if satisfied: move(db, c, "CLOSED", "Customer satisfied")
    elif datetime.utcnow() - c.delivered_at > timedelta(days=7):
        raise FlowError(409, "E07", "Reopen window (7 days) has passed")
    else: move(db, c, "REOPENED", "Not satisfied: back to diagnosis")
    db.commit(); return c
    
# ---------- Go back one step (undo a mistake) ----------
# current status -> the statuses it can have come from.
# We go back to the MOST RECENT one of these in the complaint history.
BACK_FROM = {
    "TRIAGED": ["FIRST_LEVEL_HELP"],
    "DIAGNOSING": ["TRIAGED"],
    "QUOTE_PENDING": ["DIAGNOSING", "REOPENED"],
    "QUOTE_SENT": ["QUOTE_PENDING"],
    "REPAIRING": ["DIAGNOSING", "REOPENED", "QUOTE_SENT"],
    "QC_PASSED": ["REPAIRING"],
    "REPLACEMENT_PENDING": ["DIAGNOSING", "REOPENED"],
    "REPLACEMENT_APPROVED": ["FAST_TRACK", "REPLACEMENT_PENDING"],
    "DISPATCHED": ["QC_PASSED", "REPLACEMENT_APPROVED"],
    "DELIVERED": ["DISPATCHED"],
}

def previous_status(c):
    """Status before the current step, or None when this status cannot go back."""
    for h in reversed(c.history):
        if h.status in BACK_FROM.get(c.status, ()):
            return h.status
    return None

def go_back(db, c, reason=None):
    prev = previous_status(c)
    if prev is None:
        raise FlowError(409, "E14", f"Cannot go back from status {c.status}")
    undone = c.status
    # clear what the undone step saved, so it can be entered again
    if undone == "TRIAGED":
        c.issue_code = c.priority = c.sla_due = c.pickup_type = None
    elif undone == "DIAGNOSING":
        recv = next((h for h in reversed(c.history) if h.status == "DIAGNOSING"
                     and (h.note or "").startswith(("Customer damage found", "Phone received"))), None)
        if recv and recv.note.startswith("Customer damage found"):
            c.warranty_status = "IN_WARRANTY"      # undo the customer-damage re-classification
        c.job_card_no = c.condition_notes = None
    elif undone == "QUOTE_SENT":
        c.quote_amount = None
    elif undone == "REPLACEMENT_APPROVED":
        if c.new_imei:
            if db.query(Complaint).filter(Complaint.imei == c.new_imei).count():
                raise FlowError(409, "E15", "The new phone already has a complaint, so the replacement cannot be undone")
            db.query(Device).filter_by(imei=c.new_imei).delete()   # remove the new phone from the Manufacturing DB
        c.new_imei, c.old_phone_collected = None, False
    elif undone == "DISPATCHED":
        c.tracking_no = c.handover_otp = None
    elif undone == "DELIVERED":
        c.delivered_at = None
    note = f"Moved back from {undone} to {prev}"
    if reason:
        note += f": {reason}"
    move(db, c, prev, note)
    db.commit(); return c