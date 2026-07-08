from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.api.deps import get_timezone

app = FastAPI()


@app.get("/probe")
def probe(tz: str = Depends(get_timezone)):
    return {"tz": tz}


client = TestClient(app)


def test_valid_timezone():
    r = client.get("/probe", headers={"X-Timezone": "Asia/Shanghai"})
    assert r.status_code == 200
    assert r.json() == {"tz": "Asia/Shanghai"}


def test_utc_timezone():
    r = client.get("/probe", headers={"X-Timezone": "UTC"})
    assert r.status_code == 200


def test_missing_timezone_header_returns_400():
    r = client.get("/probe")
    assert r.status_code == 400


def test_invalid_timezone_returns_400():
    r = client.get("/probe", headers={"X-Timezone": "Not/A_Real_Zone"})
    assert r.status_code == 400
