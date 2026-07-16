from pathlib import Path

import ezdxf
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["convert"] is True


def test_convert_dxf_batch(tmp_path: Path):
    paths = []
    for i, word in enumerate(["切换开关", "真空泡"]):
        p = tmp_path / f"t{i}.dxf"
        doc = ezdxf.new("R2010")
        doc.modelspace().add_text(word, dxfattribs={"height": 2, "insert": (0, 0)})
        doc.saveas(p)
        paths.append(p)

    files = [
        ("files", (p.name, p.read_bytes(), "application/octet-stream")) for p in paths
    ]
    r = client.post("/v1/convert", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["job_id"]
    assert len(data["results"]) == 2
    assert all(x["ok"] for x in data["results"])
    assert data["zip_url"]

    z = client.get(data["zip_url"])
    assert z.status_code == 200
    assert z.headers["content-type"].startswith("application/zip")
    assert len(z.content) > 100
