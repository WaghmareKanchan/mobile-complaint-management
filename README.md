# mobile-complaint-management
Mobile phone warranty complaint management system with IMEI verification, warranty check, SLA priority, repair/replacement workflow and bulk upload. Built with FastAPI, MySQL and plain HTML/CSS/JS in an MVC structure.


A web app for handling mobile phone warranty complaints from registration to closure. It follows a complaint flowchart: IMEI verification, warranty check, triage with SLA, repair or replacement, dispatch, and customer feedback.

Built with **FastAPI**, **MySQL** and plain **HTML/CSS/JS**, in an MVC structure.

## Features
- IMEI validation (15 digits + Luhn check digit) and lookup in the manufacturing database
- Error codes E01 to E05 (invalid, not found, mismatch, duplicate, blocked)
- Warranty check from sale date and warranty months
- Fast-track replacement for dead-on-arrival phones or the third complaint on one IMEI
- Issue code, priority (Critical, High, Medium, Low) and SLA due date
- Out-of-warranty quote and customer approval
- Repair, QC, replacement, dispatch, hand-over, feedback and reopen within 7 days
- Complete status history for every complaint
- Bulk upload of complaints from a CSV file with a per-row result

## Project structure
```
app/
  models/        Model: Device, Complaint, History (SQLAlchemy)
  schemas/       Request and response shapes (Pydantic)
  controllers/   Controller: API routes
  services/      Business rules (verification, warranty, priority, workflow, bulk)
  config.py      Database and SLA settings
  database.py    Engine and session
  main.py        FastAPI app
frontend/        View: index.html, style.css, app.js
sql/schema.sql   Creates the database
tests/           End-to-end tests
```

## Requirements
- Python 3.10 or newer
- MySQL 8

## Setup
```bash
git clone https://github.com/<your-username>/mobile-complaint-management.git
cd mobile-complaint-management
pip install -r requirements.txt
```

Create the database:
```bash
mysql -u root -p < sql/schema.sql
```

Set your database settings (never commit passwords):
```bash
# Windows cmd
set DB_USER=root
set DB_PASSWORD=your_password
set DB_HOST=localhost
set DB_NAME=complaint_db

# Linux / macOS
export DB_USER=root DB_PASSWORD=your_password DB_HOST=localhost DB_NAME=complaint_db
```

Run:
```bash
python -m uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 for the web app and http://127.0.0.1:8000/docs for the API docs. Tables are created automatically on first start.

## Quick start
1. Open the **Manufacturing DB** tab and add a phone, for example IMEI `490154203237518`.
2. Open **New complaint** and register a complaint with the same IMEI.
3. Open **Complaints**, click the row and use the buttons to move it through each step until it is closed.

## API overview
| Method | Endpoint | Purpose |
|---|---|---|
| POST, GET | `/api/devices` | Add or list manufacturing records |
| POST, GET | `/api/complaints` | Register or list complaints |
| GET | `/api/complaints/{id}` | Get one complaint with history |
| POST | `/api/complaints/bulk` | Bulk upload (CSV) |
| GET | `/api/complaints/bulk/template` | CSV template |
| POST | `/api/complaints/{id}/guidance` | First-level help result |
| POST | `/api/complaints/{id}/triage` | Issue code, priority, SLA |
| POST | `/api/complaints/{id}/receive` | Phone received at service centre |
| POST | `/api/complaints/{id}/diagnose` | Repairable or not |
| POST | `/api/complaints/{id}/quote` | Send repair quote |
| POST | `/api/complaints/{id}/quote-decision` | Customer approves or declines |
| POST | `/api/complaints/{id}/repair` | Final QC result |
| POST | `/api/complaints/{id}/replacement` | Approve replacement |
| POST | `/api/complaints/{id}/dispatch` | Dispatch to dealer |
| POST | `/api/complaints/{id}/handover` | Hand over to customer |
| POST | `/api/complaints/{id}/feedback` | Close or reopen |

## Error codes
| Code | Meaning |
|---|---|
| E01 | Invalid IMEI |
| E02 | IMEI not found (complaint on hold) |
| E03 | IMEI and serial mismatch (on hold) |
| E04 | Duplicate open complaint |
| E05 | IMEI blacklisted or stolen |
| E06 | Bad bulk file or missing field |
| E07 | Reopen window (7 days) passed |
| E99 | Action not allowed in the current status |

## Tests
```bash
pytest -q
```
The tests use a temporary SQLite database, so MySQL is not needed.

## License
MIT. See [LICENSE](LICENSE).