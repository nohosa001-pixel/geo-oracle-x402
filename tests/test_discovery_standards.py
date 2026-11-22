from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_geo_discovery_standards():
    r_robots = client.get("/robots.txt")
    assert r_robots.status_code == 200
    assert "Sitemap:" in r_robots.text
    assert "LLMs-Txt:" in r_robots.text

    r_sitemap = client.get("/sitemap.xml")
    assert r_sitemap.status_code == 200
    assert "application/xml" in r_sitemap.headers["content-type"]
    assert "/.well-known/x402.json" in r_sitemap.text
    assert "2026-11-22" in r_sitemap.text

    r_x402 = client.get("/.well-known/x402.json")
    assert r_x402.status_code == 200
    data = r_x402.json()
    assert data["x402Version"] == 1
    assert data["service"] == "geo-oracle-x402"
    assert len(data["paid_endpoints"]) == 4

    r_card = client.get("/.well-known/agent-card.json")
    assert r_card.status_code == 200
    assert r_card.json()["endpoints"]["x402_manifest"] == "/.well-known/x402.json"
