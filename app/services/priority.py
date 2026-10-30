from datetime import datetime, timedelta
from app.config import SLA_HOURS

def sla_due(priority: str) -> datetime:
    return datetime.utcnow() + timedelta(hours=SLA_HOURS[priority])

def is_urgent(priority: str) -> bool:
    return priority in ("Critical", "High")
