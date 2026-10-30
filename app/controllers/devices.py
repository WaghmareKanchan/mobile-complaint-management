from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Device
from app.schemas.complaint import DeviceIn

router = APIRouter(prefix="/api/devices", tags=["manufacturing db"])

@router.post("")
def add_device(d: DeviceIn, db: Session = Depends(get_db)):
    dev = Device(**d.model_dump()); db.add(dev); db.commit()
    return {"id": dev.id}

@router.get("")
def list_devices(db: Session = Depends(get_db)):
    return [{"imei": x.imei, "serial": x.serial, "model": x.model, "sale_date": x.sale_date,
             "warranty_months": x.warranty_months, "blacklisted": x.blacklisted} for x in db.query(Device).all()]
