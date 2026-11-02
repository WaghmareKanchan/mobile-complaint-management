from pathlib import Path
import uuid
from app.models import ComplaintFile, History
from app.services.errors import FlowError

UPLOAD_DIR = Path("uploads")
TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
         "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}
MAX_MB = {"photo": 5, "video": 50}

def save(db, c, upload):
    ext = TYPES.get(upload.content_type)
    if not ext:
        raise FlowError(415, "E11", "Only JPG, PNG, WEBP photos or MP4, WEBM, MOV videos are allowed")
    kind = "photo" if upload.content_type.startswith("image/") else "video"
    UPLOAD_DIR.mkdir(exist_ok=True)
    name = uuid.uuid4().hex + ext
    path, size, too_big = UPLOAD_DIR / name, 0, False
    with open(path, "wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_MB[kind] * 1024 * 1024:
                too_big = True; break
            out.write(chunk)
    if too_big:
        path.unlink(missing_ok=True)
        raise FlowError(413, "E12", f"{kind.capitalize()} too large (max {MAX_MB[kind]} MB)")
    rec = ComplaintFile(complaint_id=c.id, kind=kind, stage=c.status, original_name=(upload.filename or name)[:255],
                        stored_name=name, content_type=upload.content_type, size=size)
    db.add(rec)
    db.add(History(complaint_id=c.id, status=c.status, note=f"{kind.capitalize()} uploaded: {rec.original_name}"[:255]))
    db.commit(); db.refresh(rec)
    return rec