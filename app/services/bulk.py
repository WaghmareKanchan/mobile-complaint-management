import csv, io, uuid
from openpyxl import Workbook, load_workbook
from app.schemas.complaint import ComplaintIn
from app.services.errors import FlowError
from app.services.workflow import register

COLS = ["customer_name", "phone", "model", "imei", "serial", "issue"]
TEMPLATE = ",".join(COLS) + "\n"
REQUIRED = ["customer_name", "phone", "imei", "issue"]

def template_xlsx() -> bytes:
    wb = Workbook(); wb.active.append(COLS)
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()

def _cell(v):
    if v is None: return ""
    if isinstance(v, float) and v.is_integer(): v = int(v)
    return str(v).strip()

def read_rows(raw: bytes, filename: str):
    if filename.lower().endswith(".xlsx"):
        data = list(load_workbook(io.BytesIO(raw), read_only=True, data_only=True).active.iter_rows(values_only=True))
        if not data: return [], []
        head = [_cell(h) for h in data[0]]
        return head, [dict(zip(head, map(_cell, r))) for r in data[1:] if any(c is not None for c in r)]
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    return reader.fieldnames or [], [{k: _cell(v) for k, v in r.items() if k} for r in reader]

def process(db, raw: bytes, filename: str = ""):
    try:
        head, data = read_rows(raw, filename)
    except Exception:
        raise FlowError(422, "E06", "File format not OK: upload the .xlsx or .csv template")
    if any(f not in head for f in REQUIRED):
        raise FlowError(422, "E06", "File format not OK: use the template columns")
    batch, rows = uuid.uuid4().hex[:8], []
    for n, r in enumerate(data, start=2):
        base = {"row": n, "imei": r.get("imei", "")}
        if any(not r.get(f) for f in REQUIRED):
            rows.append({**base, "ok": False, "code": "E06", "message": "Mandatory field missing"}); continue
        try:
            c = register(db, ComplaintIn(**{k: (v or None) for k, v in r.items() if k in COLS}), batch)
            rows.append({**base, "ok": not c.error_code, "id": c.id, "code": c.error_code, "status": c.status})
        except FlowError as e:
            rows.append({**base, "ok": False, "code": e.code, "message": e.message})
    return {"batch_id": batch, "accepted": sum(x["ok"] for x in rows), "rows": rows}