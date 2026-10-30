import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.imei import valid_imei

IMEI = "490154203237518"  # valid Luhn

def test_imei():
    assert valid_imei(IMEI) and not valid_imei("490154203237519") and not valid_imei("123")

def test_full_repair_flow():
    with TestClient(app) as c:
        c.post("/api/devices", json={"imei": IMEI, "serial": "SN1", "model": "X1",
               "sale_date": str(date.today() - timedelta(days=30)), "warranty_months": 12})
        r = c.post("/api/complaints", json={"customer_name": "A", "phone": "1", "imei": IMEI, "serial": "SN1", "issue": "no power"})
        cid = r.json()["id"]; assert r.json()["status"] == "FIRST_LEVEL_HELP"
        assert c.post("/api/complaints", json={"customer_name": "A", "phone": "1", "imei": IMEI, "issue": "x"}).json()["detail"]["code"] == "E04"
        for path, body, want in [("triage", {"issue_code": "PWR", "priority": "High"}, "TRIAGED"),
            ("receive", {}, "DIAGNOSING"), ("diagnose", {"repairable": True}, "REPAIRING"),
            ("repair", {"qc_passed": True}, "QC_PASSED"), ("dispatch", {"tracking_no": "T1"}, "DISPATCHED"),
            ("handover", None, "DELIVERED"), ("feedback", {"satisfied": True}, "CLOSED")]:
            r = c.post(f"/api/complaints/{cid}/{path}", json=body) if body is not None else c.post(f"/api/complaints/{cid}/{path}")
            assert r.json()["status"] == want, (path, r.json())

def test_errors_and_bulk():
    with TestClient(app) as c:
        assert c.post("/api/complaints", json={"customer_name": "A", "phone": "1", "imei": "123", "issue": "x"}).json()["detail"]["code"] == "E01"
        r = c.post("/api/complaints", json={"customer_name": "A", "phone": "1", "imei": "356938035643809", "issue": "x"})
        assert r.json()["error_code"] == "E02" and r.json()["status"] == "ON_HOLD"
        csv = b"customer_name,phone,model,imei,serial,issue\nB,2,,123,,bad\nC,3,,356938035643809,,x\n"
        res = c.post("/api/complaints/bulk", files={"file": ("a.csv", csv)}).json()
        assert [x["code"] for x in res["rows"]] == ["E01", "E02"]
