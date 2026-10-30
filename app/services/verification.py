from app.models import Device, Complaint
from app.services.errors import FlowError
from app.services.imei import valid_imei

def verify(db, imei, serial):
    """Returns (error_code|None, device|None, message). E01/E04/E05 raise (rejected)."""
    if not valid_imei(imei):
        raise FlowError(422, "E01", "INVALID IMEI: ask customer to re-check (dial *#06# or see box/invoice)")
    dev = db.query(Device).filter_by(imei=imei).first()
    if not dev:
        return "E02", None, "NOT FOUND: ask invoice + box label. Status = ON HOLD"
    if serial and serial.strip().upper() != dev.serial.upper():
        return "E03", dev, "MISMATCH: check box / invoice. Status = ON HOLD"
    open_c = db.query(Complaint).filter(Complaint.imei == imei,
             ~Complaint.status.in_(["CLOSED", "ON_HOLD"])).first()
    if open_c:
        raise FlowError(409, "E04", f"DUPLICATE: open complaint #{open_c.id} exists (status {open_c.status})")
    if dev.blacklisted:
        raise FlowError(403, "E05", "BLOCKED: IMEI blacklisted or stolen. Inform manufacturer")
    return None, dev, ""
