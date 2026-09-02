"""评审接口单元测试。

覆盖 /roast、/stats、/github/analyze、/meme 核心接口。
"""

from __future__ import annotations


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"]


def test_roast_returns_valid_shape(client):
    payload = {"code": "def foo():\n    x = 1\n    return x\n", "language": "python"}
    resp = client.post("/roast", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["roast_text"]
    assert 0 <= data["chaos_score"] <= 100
    assert isinstance(data["suggestions"], list) and data["suggestions"]
    assert data["id"] > 0
    assert data["code_length"] == len(payload["code"])


def test_roast_rejects_empty_code(client):
    resp = client.post("/roast", json={"code": "", "language": "python"})
    assert resp.status_code == 422


def test_roast_rejects_missing_code(client):
    resp = client.post("/roast", json={"language": "python"})
    assert resp.status_code == 422


def test_get_roast_by_id(client):
    payload = {"code": "print('hi')", "language": "python"}
    created = client.post("/roast", json=payload).json()
    resp = client.get(f"/roast/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_roast_404(client):
    resp = client.get("/roast/999999")
    assert resp.status_code == 404


def test_stats_after_roast(client):
    client.post("/roast", json={"code": "a=1", "language": "python"})
    client.post("/roast", json={"code": "b=2", "language": "python"})
    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_analyses"] == 2
    assert 0 <= data["average_chaos_score"] <= 100


def test_github_analyze_with_mock(client):
    payload = {"repo": "octocat/hello-world", "commit_sha": "abc123def456"}
    resp = client.post("/github/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["repo"] == payload["repo"]
    assert data["total_additions"] > 0
    assert data["files"]
    assert data["roast"]["roast_text"]


def test_meme_generation(client):
    created = client.post(
        "/roast", json={"code": "x = 1\n\n\n", "language": "python"}
    ).json()
    resp = client.post(f"/meme/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_id"] == created["id"]
    # 下载生成的 PNG
    png = client.get(f"/meme/{data['id']}")
    assert png.status_code == 200
    assert png.headers["content-type"] == "image/png"


def test_webhook_ping(client):
    resp = client.post(
        "/webhook/github",
        json={"zen": "Keep it logically awesome.", "hook_id": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pong"
