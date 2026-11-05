from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Device
from app.schemas.complaint import DeviceIn
from app.services.imei import valid_imei
from app.services.errors import FlowError

router = APIRouter(prefix="/api/devices", tags=["manufacturing db"])

@router.post("")
def add_device(d: DeviceIn, db: Session = Depends(get_db)):
    if not valid_imei(d.imei):
        raise FlowError(422, "E01", "Invalid IMEI: 15 digits with a correct check digit")
    if db.query(Device).filter_by(imei=d.imei).first():
        raise FlowError(409, "E08", "This IMEI is already in the Manufacturing DB")
    dev = Device(**d.model_dump()); db.add(dev); db.commit()
    return {"id": dev.id}

@router.get("")
def list_devices(db: Session = Depends(get_db)):
    return [{"imei": x.imei, "serial": x.serial, "model": x.model, "sale_date": x.sale_date,
             "warranty_months": x.warranty_months} for x in db.query(Device).all()]
