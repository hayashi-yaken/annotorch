from fastapi.testclient import TestClient

from annotorch.server import app as app_module


def test_static_served_when_built(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>annotorch-ui</html>")
    monkeypatch.setattr(app_module, "STATIC_DIR", static)
    client = TestClient(app_module.create_app(tmp_path / "root"))
    res = client.get("/")
    assert res.status_code == 200
    assert "annotorch-ui" in res.text


def test_api_still_works_with_static(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html></html>")
    monkeypatch.setattr(app_module, "STATIC_DIR", static)
    client = TestClient(app_module.create_app(tmp_path / "root"))
    assert client.get("/api/health").status_code == 200
