import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from annotorch.server.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "root")
    with TestClient(app) as c:
        yield c


def make_png_bytes(color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def create_project(client, name="p") -> str:
    return client.post("/api/projects", json={"name": name}).json()["id"]


def upload_pngs(client, pid: str, n: int) -> None:
    files = [
        ("files", (f"{k}.png", make_png_bytes((k * 60 % 256, 0, 0)), "image/png"))
        for k in range(n)
    ]
    res = client.post(f"/api/projects/{pid}/items/upload", files=files)
    assert res.status_code == 200 and res.json()["imported"] == n
