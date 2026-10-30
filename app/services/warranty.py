import calendar
from datetime import date

def add_months(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    y, mo = d.year + y, mo + 1
    return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))

def warranty_valid(dev, today=None) -> bool:
    today = today or date.today()
    return bool(dev.sale_date) and today <= add_months(dev.sale_date, dev.warranty_months or 0)
