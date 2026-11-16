def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_document(client):
    files = {"file": ("test.txt", b"this is some test content", "text/plain")}
    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.txt"
    assert "id" in data


def test_upload_rejects_unsupported_type(client):
    files = {"file": ("evil.exe", b"x", "application/octet-stream")}
    assert client.post("/api/v1/documents", files=files).status_code == 400


def test_upload_rejects_empty_text(client):
    files = {"file": ("empty.txt", b"   ", "text/plain")}
    assert client.post("/api/v1/documents", files=files).status_code == 400
