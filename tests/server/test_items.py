import json

from .conftest import create_project, make_png_bytes


def test_upload_images_and_list(client):
    pid = create_project(client)
    res = client.post(f"/api/projects/{pid}/items/upload", files=[
        ("files", ("a.png", make_png_bytes(), "image/png")),
        ("files", ("b.png", make_png_bytes((0, 255, 0)), "image/png")),
        ("files", ("c.txt", b"hello", "text/plain")),
    ])
    assert res.status_code == 200
    report = res.json()
    assert report["imported"] == 2
    assert len(report["skipped"]) == 1

    items = client.get(f"/api/projects/{pid}/items").json()
    assert len(items) == 2
    assert all(i["modality"] == "image" for i in items)


def test_item_file_served(client):
    pid = create_project(client)
    client.post(f"/api/projects/{pid}/items/upload",
                files=[("files", ("a.png", make_png_bytes(), "image/png"))])
    item = client.get(f"/api/projects/{pid}/items").json()[0]
    res = client.get(f"/api/projects/{pid}/items/{item['id']}/file")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_item_file_unknown_404(client):
    pid = create_project(client)
    assert client.get(f"/api/projects/{pid}/items/nope/file").status_code == 404


def test_upload_texts_jsonl(client):
    pid = create_project(client)
    lines = "\n".join([json.dumps({"text": "hello"}), json.dumps({"text": "world"})])
    res = client.post(f"/api/projects/{pid}/items/upload-texts",
                      files={"file": ("t.jsonl", lines.encode(), "application/jsonl")})
    assert res.status_code == 200
    assert res.json()["imported"] == 2
    items = client.get(f"/api/projects/{pid}/items").json()
    assert items[0]["text"] == "hello"


def test_upload_texts_wrong_extension_400(client):
    pid = create_project(client)
    res = client.post(f"/api/projects/{pid}/items/upload-texts",
                      files={"file": ("t.txt", b"x", "text/plain")})
    assert res.status_code == 400


def test_import_folder(client, tmp_path):
    from PIL import Image

    pid = create_project(client)
    src = tmp_path / "folder"
    src.mkdir()
    Image.new("RGB", (8, 8)).save(src / "x.png")
    res = client.post(f"/api/projects/{pid}/items/import-folder",
                      json={"path": str(src)})
    assert res.status_code == 200
    assert res.json()["imported"] == 1


def test_import_folder_bad_path_400(client):
    pid = create_project(client)
    res = client.post(f"/api/projects/{pid}/items/import-folder",
                      json={"path": "/no/such/dir"})
    assert res.status_code == 400
