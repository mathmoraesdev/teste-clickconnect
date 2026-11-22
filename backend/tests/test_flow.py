from fastapi.testclient import TestClient

from api import app
from api.deps import erp

c = TestClient(app)
CUST = {"name": "Maria Silva", "email": "maria@x.com", "phone": "51999999999"}


def order(store="s1", items=None, token=None):
    return c.post(
        "/api/v1/orders",
        json={
            "customer": CUST,
            "store_id": store,
            "items": items or [{"product_id": "p4", "quantity": 2}],
            "payment": {"method": "card", "token": token},
        },
    )


def test_catalog_and_availability():
    assert len(c.get("/api/v1/products").json()) == 6
    assert c.get("/api/v1/stores/s1/availability").status_code == 200
    assert c.get("/api/v1/products/zzz").status_code == 404


def test_pickup_options_recommend():
    r = c.post(
        "/api/v1/pickup/options",
        json={
            "items": [{"product_id": "p1", "quantity": 1}],
            "lat": -29.80,
            "lng": -51.16,
        },
    ).json()
    rec = [o for o in r if o["recommended"]]
    assert rec[0]["store"]["id"] == "s3"
    assert not next(o for o in r if o["store"]["id"] == "s2")["can_fulfill"]


def test_full_flow():
    before = erp.available("s1", "p4")
    o = order().json()
    assert o["status"] == "confirmed" and len(o["pickup_code"]) == 6
    assert erp.available("s1", "p4") == before - 2
    oid, code = o["id"], o["pickup_code"]
    assert (
        c.post("/api/v1/stores/s1/pickup/validate", json={"code": code}).status_code
        == 409
    )
    assert c.post(f"/api/v1/orders/{oid}/ready").status_code == 409
    assert (
        c.post(f"/api/v1/orders/{oid}/start-preparing").json()["status"] == "preparing"
    )
    assert c.post(f"/api/v1/orders/{oid}/ready").json()["status"] == "ready"
    kinds = [n["kind"] for n in c.get(f"/api/v1/orders/{oid}/notifications").json()]
    assert kinds == ["order_confirmed", "order_ready"]
    assert (
        c.post("/api/v1/stores/s2/pickup/validate", json={"code": code}).status_code
        == 404
    )
    done = c.post(
        "/api/v1/stores/s1/pickup/validate", json={"code": code.lower()}
    ).json()
    assert done["status"] == "completed" and done["picked_up_at"]
    assert erp.available("s1", "p4") == before - 2
    assert c.get(f"/api/v1/orders/{oid}/status").json()["label"] == "Retirado"
    assert any(
        x["id"] == oid
        for x in c.get("/api/v1/orders", params={"email": "maria@x.com"}).json()
    )


def test_declined_payment_releases_stock():
    before = erp.available("s1", "p2")
    r = order(items=[{"product_id": "p2", "quantity": 3}], token="recusado")
    assert r.status_code == 402
    assert erp.available("s1", "p2") == before


def test_no_stock_and_cancel():
    assert (
        order(store="s1", items=[{"product_id": "p5", "quantity": 1}]).status_code
        == 409
    )
    before = erp.available("s1", "p6")
    oid = order(items=[{"product_id": "p6", "quantity": 1}]).json()["id"]
    assert erp.available("s1", "p6") == before - 1
    assert c.post(f"/api/v1/orders/{oid}/cancel").json()["status"] == "cancelled"
    assert erp.available("s1", "p6") == before
    assert c.post(f"/api/v1/orders/{oid}/cancel").status_code == 409


def test_validation():
    r = c.post(
        "/api/v1/orders",
        json={
            "customer": {**CUST, "email": "ruim"},
            "store_id": "s1",
            "items": [{"product_id": "p4", "quantity": 1}],
            "payment": {"method": "pix"},
        },
    )
    assert r.status_code == 422
