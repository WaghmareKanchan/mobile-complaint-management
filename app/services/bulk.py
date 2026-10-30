import csv, io, uuid
from app.schemas.complaint import ComplaintIn
from app.services.errors import FlowError
from app.services.workflow import register

TEMPLATE = "customer_name,phone,model,imei,serial,issue\n"
REQUIRED = ["customer_name", "phone", "imei", "issue"]

def process(db, raw: bytes):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames or any(f not in reader.fieldnames for f in REQUIRED):
        raise FlowError(422, "E06", "File format not OK: use the template columns")
    batch, rows = uuid.uuid4().hex[:8], []
    for n, r in enumerate(reader, start=2):
        if any(not (r.get(f) or "").strip() for f in REQUIRED):
            rows.append({"row": n, "ok": False, "code": "E06", "message": "Mandatory field missing"}); continue
        try:
            c = register(db, ComplaintIn(**{k: (v or "").strip() or None for k, v in r.items() if k}), batch)
            rows.append({"row": n, "ok": not c.error_code, "id": c.id, "code": c.error_code, "status": c.status})
        except FlowError as e:
            rows.append({"row": n, "ok": False, "code": e.code, "message": e.message})
    return {"batch_id": batch, "accepted": sum(x["ok"] for x in rows), "rows": rows}
