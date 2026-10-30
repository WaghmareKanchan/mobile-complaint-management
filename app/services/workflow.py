from datetime import datetime, timedelta
from app.models import Complaint, History
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
    prior = db.query(Complaint).filter(Complaint.imei == d.imei, Complaint.id != c.id,
                                       Complaint.status == "CLOSED").count()
    if ok and (d.dead_on_arrival or prior >= 2):
        c.fast_track = True
        move(db, c, "FAST_TRACK", "Dead on arrival / same issue 3 times: fast-track replacement")
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
    note = f"{issue_code} / {priority}, SLA {c.sla_due:%Y-%m-%d %H:%M}"
    if is_urgent(priority):
        note = "SAFETY: STOP using, STOP charging, keep from heat. Urgent pickup within 24h. " + note
    move(db, c, "TRIAGED", note)
    db.commit(); return c

def receive(db, c, customer_damage):
    require(c, "TRIAGED")
    if customer_damage and c.warranty_status == "IN_WARRANTY":
        c.warranty_status = "OUT_OF_WARRANTY"
        move(db, c, "DIAGNOSING", "Customer damage found: re-classified OUT_OF_WARRANTY")
    else:
        move(db, c, "DIAGNOSING", "Received at service centre, job card created")
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
    move(db, c, "QUOTE_SENT", f"Quote sent: {amount}")
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

def approve_replacement(db, c, new_imei):
    require(c, "FAST_TRACK", "REPLACEMENT_PENDING")
    if not valid_imei(new_imei):
        raise FlowError(422, "E01", "New IMEI is invalid")
    c.new_imei = new_imei
    move(db, c, "REPLACEMENT_APPROVED", f"Replacement linked to new IMEI {new_imei}, new warranty")
    db.commit(); return c

def dispatch(db, c, tracking_no):
    require(c, "QC_PASSED", "REPLACEMENT_APPROVED")
    c.tracking_no = tracking_no
    move(db, c, "DISPATCHED", f"Courier {tracking_no}")
    db.commit(); return c

def handover(db, c):
    require(c, "DISPATCHED")
    c.delivered_at = datetime.utcnow()
    move(db, c, "DELIVERED", "Customer checked, OTP/signature taken")
    db.commit(); return c

def feedback(db, c, satisfied):
    require(c, "DELIVERED")
    if satisfied: move(db, c, "CLOSED", "Customer satisfied")
    elif datetime.utcnow() - c.delivered_at > timedelta(days=7):
        raise FlowError(409, "E07", "Reopen window (7 days) has passed")
    else: move(db, c, "REOPENED", "Not satisfied: back to diagnosis")
    db.commit(); return c
