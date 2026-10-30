from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
import app.models  # noqa
from app.controllers import complaints, devices
from app.services.errors import FlowError

@asynccontextmanager
async def lifespan(_):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title="Mobile Complaint Management", lifespan=lifespan)

@app.exception_handler(FlowError)
async def flow_error(_: Request, e: FlowError):
    return JSONResponse(status_code=e.status_code, content={"detail": {"code": e.code, "message": e.message}})

app.include_router(complaints.router)
app.include_router(devices.router)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
