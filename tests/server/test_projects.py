def test_create_and_list_projects(client):
    res = client.post("/api/projects", json={"name": "demo", "description": "d"})
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "demo"
    listed = client.get("/api/projects").json()
    assert [p["id"] for p in listed] == [body["id"]]


def test_rename_project(client):
    pid = client.post("/api/projects", json={"name": "old"}).json()["id"]
    res = client.patch(f"/api/projects/{pid}", json={"name": "new"})
    assert res.status_code == 200
    assert res.json()["name"] == "new"
    assert [p["name"] for p in client.get("/api/projects").json()] == ["new"]


def test_rename_project_blank_name_400(client):
    pid = client.post("/api/projects", json={"name": "old"}).json()["id"]
    assert client.patch(f"/api/projects/{pid}", json={"name": " "}).status_code == 400


def test_rename_unknown_project_404(client):
    assert client.patch("/api/projects/nope", json={"name": "x"}).status_code == 404


def test_delete_project(client):
    pid = client.post("/api/projects", json={"name": "x"}).json()["id"]
    assert client.delete(f"/api/projects/{pid}").json() == {"ok": True}
    assert client.get("/api/projects").json() == []


def test_delete_unknown_project_404(client):
    assert client.delete("/api/projects/nope").status_code == 404


def test_delete_project_traversal_rejected(client):
    """project_id='..' percent-encoded as '%2E%2E' bypasses the httpx client's
    own path normalization, so the raw '..' segment reaches the ASGI app and
    is routed to delete_project(pid='..'). Without the workspace-boundary
    guard this hits shutil.rmtree on the workspace root; it must 404 instead."""
    pid = client.post("/api/projects", json={"name": "x"}).json()["id"]

    res = client.delete("/api/projects/%2E%2E")
    assert res.status_code == 404

    listed = client.get("/api/projects").json()
    assert [p["id"] for p in listed] == [pid]
