def test_create_and_list_projects(client):
    res = client.post("/api/projects", json={"name": "demo", "description": "d"})
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "demo"
    listed = client.get("/api/projects").json()
    assert [p["id"] for p in listed] == [body["id"]]


def test_delete_project(client):
    pid = client.post("/api/projects", json={"name": "x"}).json()["id"]
    assert client.delete(f"/api/projects/{pid}").json() == {"ok": True}
    assert client.get("/api/projects").json() == []


def test_delete_unknown_project_404(client):
    assert client.delete("/api/projects/nope").status_code == 404
