from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import PlainTextResponse, Response, FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Complaint, ComplaintFile
from app.schemas import complaint as s
from app.services import workflow as w, bulk, files as fs
from app.services.errors import FlowError

router = APIRouter(prefix="/api/complaints", tags=["complaints"])

def get_or_404(db, id):
    c = db.get(Complaint, id)
    if not c: raise FlowError(404, "E00", "Complaint not found")
    return c

@router.post("", response_model=s.ComplaintOut)
def create(d: s.ComplaintIn, db: Session = Depends(get_db)): return w.register(db, d)

@router.get("", response_model=list[s.ComplaintOut])
def list_all(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Complaint).order_by(Complaint.id.desc())
    return (q.filter(Complaint.status == status) if status else q).limit(200).all()

@router.post("/bulk")
def bulk_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return bulk.process(db, file.file.read(), file.filename or "")

@router.get("/bulk/template.xlsx")
def template_xlsx():
    return Response(bulk.template_xlsx(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=complaints_template.xlsx"})

@router.get("/{id}", response_model=s.ComplaintOut)
def get_one(id: int, db: Session = Depends(get_db)): return get_or_404(db, id)

def action(path, schema, fn):
    def handler(id: int, b: schema, db: Session = Depends(get_db)):
        return fn(db, get_or_404(db, id), **b.model_dump())
    handler.__name__ = path.replace("-", "_")
    router.post("/{id}/" + path, response_model=s.ComplaintOut)(handler)

action("guidance", s.GuidanceIn, w.guidance)
action("triage", s.TriageIn, w.triage)
action("receive", s.ReceiveIn, w.receive)
action("diagnose", s.DiagnoseIn, w.diagnose)
action("quote", s.QuoteIn, w.send_quote)
action("quote-decision", s.DecisionIn, w.quote_decision)
action("repair", s.RepairIn, w.finish_repair)
action("replacement", s.ReplacementIn, w.approve_replacement)
action("dispatch", s.DispatchIn, w.dispatch)
action("back", s.BackIn, w.go_back)
action("feedback", s.FeedbackIn, w.feedback)
action("handover", s.HandoverIn, w.handover)


@router.post("/{id}/files", response_model=s.FileOut)
def upload_file(id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return fs.save(db, get_or_404(db, id), file)

@router.get("/{id}/files/{fid}")
def get_file(id: int, fid: int, db: Session = Depends(get_db)):
    f = db.get(ComplaintFile, fid)
    if not f or f.complaint_id != id: raise FlowError(404, "E00", "File not found")
    return FileResponse(fs.UPLOAD_DIR / f.stored_name, media_type=f.content_type)
