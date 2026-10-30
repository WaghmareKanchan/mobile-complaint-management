from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Complaint
from app.schemas import complaint as s
from app.services import workflow as w, bulk
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
    return bulk.process(db, file.file.read())

@router.get("/bulk/template", response_class=PlainTextResponse)
def template(): return bulk.TEMPLATE

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
action("feedback", s.FeedbackIn, w.feedback)

@router.post("/{id}/handover", response_model=s.ComplaintOut)
def handover(id: int, db: Session = Depends(get_db)): return w.handover(db, get_or_404(db, id))
